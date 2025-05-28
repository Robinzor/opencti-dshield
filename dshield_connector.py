import requests
import json
from datetime import datetime
from typing import Dict, List, Any
import os
import argparse
import logging
from dotenv import load_dotenv
from pycti import OpenCTIConnectorHelper, get_config_variable
import time
import stix2

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DShieldConnector:
    def __init__(self):
        # Create config dictionary from environment variables
        config = {
            "opencti": {
                "url": os.getenv("OPENCTI_API_URL"),
                "token": os.getenv("OPENCTI_API_KEY"),
                "verify_ssl": os.getenv("OPENCTI_VERIFY_SSL", "false").lower() == "true"
            },
            "connector": {
                "id": "dshield-connector",
                "type": "EXTERNAL_IMPORT",
                "name": "DShield Connector",
                "scope": "dshield",
                "confidence_level": int(os.getenv("DHSHIELD_CONFIDENCE_LEVEL", "60")),
                "log_level": "info"
            }
        }
        
        self.helper = OpenCTIConnectorHelper(config)
        
        # Get configuration values
        self.interval = int(os.getenv("DHSHIELD_INTERVAL", "300"))
        self.update_existing_data = os.getenv("DHSHIELD_UPDATE_EXISTING_DATA", "true").lower() == "true"
        self.score = int(os.getenv("DHSHIELD_CONFIDENCE_LEVEL", "60"))
        self.update_frequency = int(os.getenv("DHSHIELD_UPDATE_FREQUENCY", "300"))
        
        # Create organization
        external_reference_org = self.helper.api.external_reference.create(
            source_name="dshield.org",
            url="https://dshield.org/",
        )
        self.organization = self.helper.api.identity.create(
            type="Organization",
            name="DShield",
            description="DShield Intel Feed importer",
            externalReferences=[external_reference_org["id"]],
        )

    def get_label(self, label_value, color="#ffa500"):
        """Controleert of een label bestaat, zo niet wordt het aangemaakt."""
        logger.info(f"Checking for label: {label_value}")
        labels = self.helper.api.label.list(search=label_value)
        for label in labels:
            if label["value"].lower() == label_value.lower():
                logger.info(f"Found existing label: {label_value}")
                return label["id"]
        logger.info(f"Creating new label: {label_value}")
        new_label = self.helper.api.label.create(
            value=label_value, color=color)
        return new_label["id"]

    def create_observable(
        self,
        observable_key,
        observable_value,
        description,
        observable_type,
        external_reference_id,
        labels
    ):
        # Create observable
        observable = self.helper.api.stix_cyber_observable.create(
            simple_observable_key=observable_key,
            simple_observable_value=observable_value,
            objectMarking=[stix2.TLP_GREEN["id"]],
            externalReferences=[external_reference_id],
            createdBy=self.organization["id"],
            x_opencti_score=self.score,
            x_opencti_create_indicator=True,
            x_opencti_main_observable_type=observable_type,
        )

        # Add labels to the observable with delay between operations
        if observable and labels:
            for label in labels:
                try:
                    label_id = self.get_label(label)
                    if label_id:
                        time.sleep(0.5)  # Add delay between operations
                        self.helper.api.stix_cyber_observable.add_label(
                            id=observable["id"], label_id=label_id)
                except Exception as e:
                    self.helper.log_error(
                        f"Failed to add label {label} to {observable_value}: {str(e)}")
                    time.sleep(0.5)  # Add longer delay after error
                    continue

        return observable

    def fetch_dshield_data(self) -> List[Dict[str, Any]]:
        """Fetch data from DShield Intel Feed API."""
        try:
            # Correct DShield Intel Feed URL
            response = requests.get('https://isc.sans.edu/api/intelfeed?json')
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched {len(data)} entries from DShield")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching DShield data: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing DShield data: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching DShield data: {str(e)}")
            return []

    def extract_labels(self, data: List[Dict[str, Any]]) -> List[str]:
        """Extract unique labels from DShield data."""
        labels = set()
        for entry in data:
            if 'description' in entry:
                label = entry['description'].lower()
                labels.add(label)
        logger.info(f"Extracted unique labels: {list(labels)}")
        return list(labels)

    def create_opencti_objects(self, data: List[Dict[str, Any]], test_mode: bool = False) -> Dict[str, Any]:
        """Create OpenCTI compatible objects from DShield data."""
        output = {
            "labels": [],
            "objects": []
        }

        # Extract and create labels
        labels = self.extract_labels(data)
        output["labels"] = labels
        logger.info(f"Total unique labels found: {len(labels)}")

        # Create external reference
        external_reference = self.helper.api.external_reference.create(
            source_name="dshield.org",
            url="https://isc.sans.edu/api/intelfeed?json"
        )

        # Process each entry
        for entry in data:
            if 'ip' not in entry:
                continue

            # Create base labels
            entry_labels = ["dshield"]  # Base label
            if 'description' in entry:
                entry_labels.append(entry['description'].lower())  # Type-specific label
            logger.info(f"Creating observable for IP {entry['ip']} with labels: {entry_labels}")

            # Create IP observable
            ip_obs = self.create_observable(
                "IPv4-Addr.value",
                entry['ip'],
                f"DShield Intel Feed entry for {entry['ip']}",
                "IPv4-Addr",
                external_reference["id"],
                entry_labels
            )

            if ip_obs:
                output["objects"].append({
                    "type": "ipv4-addr",
                    "value": entry['ip'],
                    "labels": entry_labels
                })
                logger.info(f"Successfully created observable for IP {entry['ip']}")

        logger.info(f"Total objects created: {len(output['objects'])}")
        return output

    def save_to_json(self, data: Dict[str, Any], filename: str = "dshield_export.json"):
        """Save data to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")

    def run(self, test_mode: bool = False):
        """Run the connector."""
        try:
            # Fetch data from DShield
            logger.info("Fetching data from DShield...")
            data = self.fetch_dshield_data()
            if not data:
                logger.error("No data received from DShield")
                return

            # Create OpenCTI objects
            logger.info("Creating OpenCTI objects...")
            output = self.create_opencti_objects(data, test_mode)

            # Save to JSON file
            logger.info("Saving data to JSON file...")
            self.save_to_json(output)

            logger.info("Connector run completed successfully")

        except Exception as e:
            logger.error(f"Error in connector run: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='DShield OpenCTI Connector')
    parser.add_argument('-t', '--test', action='store_true', help='Run in test mode (no OpenCTI integration)')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    connector = DShieldConnector()
    connector.run(test_mode=args.test)

if __name__ == "__main__":
    main() 