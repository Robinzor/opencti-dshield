# DShield OpenCTI Connector

This connector fetches data from the DShield Intel Feed API and prepares it for import into OpenCTI.

## Features

- Fetches data from DShield Intel Feed API
- Creates appropriate labels for different types of IP addresses
- Formats data in OpenCTI compatible format
- Saves output to a JSON file for later import
- Supports test mode for data validation without OpenCTI integration
- Docker support for easy deployment

## Installation

### Local Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Docker Installation

1. Clone this repository
2. Copy the example environment file:
```bash
cp .env.example .env
```
3. Edit `.env` with your OpenCTI connection details

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# OpenCTI Configuration
OPENCTI_URL=http://localhost:8080  # Your OpenCTI instance URL
OPENCTI_TOKEN=your-api-token       # Your OpenCTI API token

# Optional: Proxy settings if needed
# HTTP_PROXY=http://proxy:port
# HTTPS_PROXY=http://proxy:port
```

To get your OpenCTI API token:
1. Log in to your OpenCTI instance
2. Go to Settings > Access Tokens
3. Create a new token with appropriate permissions

## Usage

### Local Usage

#### Normal Mode (with OpenCTI integration)

```bash
python dshield_connector.py
```

#### Test Mode (without OpenCTI integration)

```bash
python dshield_connector.py -t
```

#### Debug Mode

```bash
python dshield_connector.py -d
```

### Docker Usage

#### Build and Run

```bash
# Build the container
docker-compose build

# Run in test mode (default)
docker-compose up

# Run in normal mode
docker-compose run --rm dshield-connector

# Run with debug logging
docker-compose run --rm dshield-connector -d
```

The connector will:
1. Fetch data from DShield Intel Feed
2. Create labels in OpenCTI (unless in test mode)
3. Create OpenCTI compatible objects
4. Save the output to `data/dshield_export.json`

## Output Format

The script creates a JSON file with the following structure:
- `labels`: List of labels used to categorize IP addresses
- `objects`: List of IPv4 address objects with their associated labels

## Labels

Labels are dynamically extracted from the DShield feed data. Common labels include:
- webscanner: Web scanning activity
- dshieldssh: SSH scanning activity
- mastodon: Mastodon instance
- ntpservers: NTP server
- tldns: TLDNS server

## Importing to OpenCTI

The generated JSON file can be imported into OpenCTI using the platform's import functionality. In normal mode, the labels and objects will be automatically created in OpenCTI.

## Troubleshooting

1. If you get authentication errors:
   - Check if your OpenCTI token is valid
   - Verify the OPENCTI_URL is correct
   - Ensure your token has the necessary permissions

2. If labels are not created:
   - Check OpenCTI logs for any errors
   - Verify you have write permissions in OpenCTI
   - Try running in test mode first to validate the data

3. Docker-specific issues:
   - Ensure the `.env` file is properly mounted
   - Check container logs: `docker-compose logs`
   - Verify volume permissions for the data directory 