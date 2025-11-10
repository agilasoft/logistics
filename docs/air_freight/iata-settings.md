# IATA Settings

## Overview

IATA Settings is a configuration document that stores IATA (International Air Transport Association) integration settings for the Air Freight module. This document is used to configure IATA services including Cargo-XML, CASSLink, TACT, and other IATA-related integrations.

## Purpose

The IATA Settings document is used to:
- Configure Cargo-XML integration for IATA message exchange
- Set up CASSLink (Cargo Accounts Settlement System) integration
- Configure TACT (The Air Cargo Tariff) subscription
- Enable Dangerous Goods AutoCheck
- Configure other IATA-related integrations
- Set up testing and debug modes

## Access

Navigate to **Air Freight > Setup > IATA Settings**

## Document Structure

The IATA Settings document contains the following sections:

### Cargo-XML Configuration

Cargo-XML is the IATA standard for electronic messaging in air cargo operations.

- **Enable Cargo-XML**: Checkbox to enable Cargo-XML integration
- **Cargo-XML Endpoint URL**: API endpoint URL for Cargo-XML services
- **Username**: Username for Cargo-XML authentication
- **Password**: Password for Cargo-XML authentication

#### Configuration Steps

1. Check **Enable Cargo-XML** to enable the integration
2. Enter **Cargo-XML Endpoint URL** (provided by your IATA service provider)
3. Enter **Username** for authentication
4. Enter **Password** for authentication
5. Save the settings

### Dangerous Goods AutoCheck

Dangerous Goods AutoCheck is an IATA service for automated DG compliance checking.

- **Enable DG AutoCheck**: Checkbox to enable Dangerous Goods AutoCheck
- **DG AutoCheck API Key**: API key for DG AutoCheck service

#### Configuration Steps

1. Check **Enable DG AutoCheck** to enable the service
2. Enter **DG AutoCheck API Key** (obtained from IATA)
3. Save the settings

### CASSLink Configuration

CASSLink is IATA's Cargo Accounts Settlement System for automated billing and settlement.

- **Enable CASSLink**: Checkbox to enable CASSLink integration
- **CASS Participant Code**: Your CASS participant code
- **CASS API Endpoint**: API endpoint URL for CASSLink services

#### Configuration Steps

1. Check **Enable CASSLink** to enable the integration
2. Enter **CASS Participant Code** (assigned by IATA)
3. Enter **CASS API Endpoint** (provided by IATA)
4. Save the settings

### TACT Configuration

TACT (The Air Cargo Tariff) provides air cargo rate information and tariff data.

- **Enable TACT Subscription**: Checkbox to enable TACT subscription
- **TACT API Key**: API key for TACT subscription
- **TACT Endpoint**: API endpoint URL for TACT services

#### Configuration Steps

1. Check **Enable TACT Subscription** to enable the service
2. Enter **TACT API Key** (obtained from IATA)
3. Enter **TACT Endpoint** (provided by IATA)
4. Save the settings

### Other Integrations

Additional IATA-related integrations:

- **Enable Net Rates**: Checkbox to enable net rates integration
- **Enable Track & Trace**: Checkbox to enable track and trace integration
- **Enable EPIC Partner Verification**: Checkbox to enable EPIC (e-Freight Partner Identification Code) partner verification

#### Configuration Steps

1. Check the appropriate integration checkboxes as needed
2. Save the settings

### Testing & Debug

Testing and debugging options:

- **Test Mode**: Checkbox to enable test mode
- **Test Endpoint URL**: Test endpoint URL for testing integrations
- **Enable Debug Logging**: Checkbox to enable debug logging

#### Configuration Steps

1. Check **Test Mode** to enable testing mode
2. Enter **Test Endpoint URL** if using a test environment
3. Check **Enable Debug Logging** to enable detailed logging
4. Save the settings

## Key Settings Explained

### Cargo-XML

Cargo-XML is the IATA standard for electronic messaging in air cargo:

- Enables electronic message exchange with airlines
- Supports automated status updates
- Facilitates electronic Air Waybill (eAWB) processing
- Reduces manual data entry

### CASSLink

CASSLink is IATA's automated billing and settlement system:

- Automates billing and settlement with airlines
- Reduces manual invoice processing
- Improves accuracy and efficiency
- Supports multiple currencies

### TACT

TACT provides air cargo rate information:

- Access to current air cargo rates
- Tariff information and updates
- Rate lookup and validation
- Supports rate calculation

### Dangerous Goods AutoCheck

Automated Dangerous Goods compliance checking:

- Validates DG declarations automatically
- Checks compliance with IATA DG regulations
- Reduces manual compliance checking
- Improves safety and compliance

## Best Practices

1. **Secure Credentials**: Keep API keys and passwords secure
2. **Test First**: Use test mode before enabling production integrations
3. **Monitor Logs**: Enable debug logging during initial setup
4. **Regular Updates**: Keep API endpoints and credentials updated
5. **Documentation**: Document any custom configurations
6. **Backup Settings**: Keep backup of settings before making changes

## Testing

Before enabling production integrations:

1. Enable **Test Mode**
2. Configure **Test Endpoint URL** if applicable
3. Enable **Debug Logging** to monitor integration activity
4. Test each integration individually
5. Verify message processing and responses
6. Disable test mode when ready for production

## Troubleshooting

### Issue: Cargo-XML messages not processing
**Solution**: 
- Verify endpoint URL is correct
- Check username and password
- Enable debug logging to see error messages
- Verify network connectivity

### Issue: CASSLink not connecting
**Solution**:
- Verify CASS Participant Code is correct
- Check API endpoint URL
- Verify network connectivity
- Contact IATA support if needed

### Issue: TACT rates not updating
**Solution**:
- Verify TACT API key is valid
- Check TACT endpoint URL
- Verify subscription is active
- Check API call limits

## Security Considerations

- **API Keys**: Store API keys securely and never share them
- **Passwords**: Use strong passwords and change them regularly
- **Test Mode**: Always use test mode for initial testing
- **Debug Logging**: Disable debug logging in production to avoid exposing sensitive information

## Related Documents

- **Air Shipment**: Uses IATA settings for status updates
- **Master Air Waybill**: Uses IATA settings for manifest processing
- **IATA Message Queue**: Processes IATA messages based on settings

## Next Steps

- Review [Setup Guide](setup.md) for initial configuration
- Learn about [Air Shipment](air-shipment.md) IATA integration
- Understand [Master Air Waybill](master-air-waybill.md) operations

---

*For detailed setup instructions, refer to the [Setup Guide](setup.md).*

