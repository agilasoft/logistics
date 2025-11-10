# Flight Schedule Settings

## Overview

Flight Schedule Settings is a configuration document that stores flight schedule integration settings for the Air Freight module. This document is used to configure flight schedule data providers, synchronization settings, and real-time tracking options.

## Purpose

The Flight Schedule Settings document is used to:
- Configure flight schedule data providers (OpenSky, AviationStack, Aviation Edge, FlightAware)
- Set up automatic flight schedule synchronization
- Configure real-time flight tracking
- Manage API call limits and data retention
- Set up testing and debug modes

## Access

Navigate to **Air Freight > Setup > Flight Schedule Settings**

## Document Structure

The Flight Schedule Settings document contains the following sections:

### General Settings

- **Default Provider**: Primary flight schedule data provider (required)
  - OpenSky Network
  - AviationStack
  - Aviation Edge
  - FlightAware
- **Enable Auto Fallback**: Checkbox to enable automatic fallback to backup providers
- **Cache Duration (Hours)**: Duration to cache flight schedule data (default: 6 hours)
- **Sync Frequency**: Frequency of automatic synchronization
  - Manual
  - Hourly
  - Every 6 Hours
  - Daily
  - Weekly
- **Enable Real-time Tracking**: Checkbox to enable real-time flight tracking
- **Max API Calls Per Hour**: Maximum number of API calls per hour (default: 1000)
- **Data Retention (Days)**: Number of days to retain flight schedule data (default: 90 days)

### OpenSky Network (Free/Open Source)

OpenSky Network is a free, open-source flight tracking service.

- **Enable OpenSky Network**: Checkbox to enable OpenSky Network (default: enabled)
- **OpenSky Username**: Username for OpenSky Network (optional)
- **OpenSky Password**: Password for OpenSky Network (optional)
- **OpenSky API Endpoint**: API endpoint URL (default: https://opensky-network.org/api)

#### Configuration Steps

1. Check **Enable OpenSky Network** to enable the provider
2. Enter **OpenSky Username** if you have an account (optional, increases rate limits)
3. Enter **OpenSky Password** if you have an account (optional)
4. Verify **OpenSky API Endpoint** is correct
5. Save the settings

### AviationStack API

AviationStack is a commercial flight data API provider.

- **Enable AviationStack**: Checkbox to enable AviationStack
- **AviationStack API Key**: API key for AviationStack
- **AviationStack Endpoint**: API endpoint URL (default: http://api.aviationstack.com/v1)

#### Configuration Steps

1. Check **Enable AviationStack** to enable the provider
2. Enter **AviationStack API Key** (obtained from AviationStack)
3. Verify **AviationStack Endpoint** is correct
4. Save the settings

### Aviation Edge API

Aviation Edge is a commercial flight data API provider.

- **Enable Aviation Edge**: Checkbox to enable Aviation Edge
- **Aviation Edge API Key**: API key for Aviation Edge
- **Aviation Edge Endpoint**: API endpoint URL (default: https://aviation-edge.com/v2/public)

#### Configuration Steps

1. Check **Enable Aviation Edge** to enable the provider
2. Enter **Aviation Edge API Key** (obtained from Aviation Edge)
3. Verify **Aviation Edge Endpoint** is correct
4. Save the settings

### FlightAware AeroAPI (Premium)

FlightAware AeroAPI is a premium flight tracking API service.

- **Enable FlightAware**: Checkbox to enable FlightAware
- **FlightAware API Key**: API key for FlightAware AeroAPI
- **FlightAware Endpoint**: API endpoint URL (default: https://aeroapi.flightaware.com/aeroapi)

#### Configuration Steps

1. Check **Enable FlightAware** to enable the provider
2. Enter **FlightAware API Key** (obtained from FlightAware)
3. Verify **FlightAware Endpoint** is correct
4. Save the settings

### Testing & Debug

Testing and debugging options:

- **Test Mode**: Checkbox to enable test mode
- **Enable Debug Logging**: Checkbox to enable debug logging
- **Test Endpoint URL**: Test endpoint URL for testing integrations

#### Configuration Steps

1. Check **Test Mode** to enable testing mode
2. Check **Enable Debug Logging** to enable detailed logging
3. Enter **Test Endpoint URL** if using a test environment
4. Save the settings

## Key Settings Explained

### Default Provider

The primary flight schedule data provider. The system will use this provider first, and fall back to other enabled providers if needed.

### Auto Fallback

When enabled, the system automatically falls back to backup providers if the primary provider fails or is unavailable. This ensures continuous flight schedule updates.

### Cache Duration

Flight schedule data is cached to reduce API calls and improve performance. The cache duration determines how long data is stored before refreshing.

### Sync Frequency

Determines how often the system automatically synchronizes flight schedule data:
- **Manual**: Synchronization only when manually triggered
- **Hourly**: Synchronization every hour
- **Every 6 Hours**: Synchronization every 6 hours
- **Daily**: Synchronization once per day
- **Weekly**: Synchronization once per week

### Real-time Tracking

When enabled, the system provides real-time flight tracking information including:
- Current position (latitude, longitude, altitude)
- Current speed and heading
- Flight status updates
- Delay information

### API Call Limits

**Max API Calls Per Hour**: Limits the number of API calls to prevent exceeding provider rate limits and avoid additional charges.

### Data Retention

**Data Retention (Days)**: Determines how long historical flight schedule data is retained in the system. Older data is automatically purged.

## Provider Comparison

### OpenSky Network
- **Cost**: Free
- **Rate Limits**: Limited (higher with account)
- **Coverage**: Global
- **Real-time**: Yes
- **Best For**: Basic flight tracking, testing, development

### AviationStack
- **Cost**: Commercial (subscription-based)
- **Rate Limits**: Based on subscription tier
- **Coverage**: Global
- **Real-time**: Yes
- **Best For**: Production use, reliable data

### Aviation Edge
- **Cost**: Commercial (subscription-based)
- **Rate Limits**: Based on subscription tier
- **Coverage**: Global
- **Real-time**: Yes
- **Best For**: Production use, comprehensive data

### FlightAware
- **Cost**: Premium (subscription-based)
- **Rate Limits**: Based on subscription tier
- **Coverage**: Global
- **Real-time**: Yes (premium features)
- **Best For**: Premium tracking, advanced features

## Best Practices

1. **Provider Selection**: Choose providers based on your needs and budget
2. **Auto Fallback**: Enable auto fallback for reliability
3. **Cache Duration**: Set appropriate cache duration to balance freshness and API usage
4. **Sync Frequency**: Set sync frequency based on your operational needs
5. **API Limits**: Monitor API call usage to avoid exceeding limits
6. **Data Retention**: Set data retention based on reporting and compliance needs
7. **Test First**: Use test mode before enabling production integrations
8. **Monitor Logs**: Enable debug logging during initial setup

## Configuration Recommendations

### For Development/Testing
- Use OpenSky Network (free)
- Enable test mode
- Enable debug logging
- Set lower sync frequency

### For Production (Small Scale)
- Use OpenSky Network or AviationStack
- Enable auto fallback
- Set hourly sync frequency
- Monitor API usage

### For Production (Large Scale)
- Use AviationStack or Aviation Edge
- Enable auto fallback with multiple providers
- Set appropriate cache duration
- Monitor API limits closely
- Consider FlightAware for premium features

## Troubleshooting

### Issue: Flight schedules not updating
**Solution**:
- Verify default provider is enabled
- Check API keys are valid
- Verify network connectivity
- Check API call limits
- Enable debug logging to see errors

### Issue: Exceeding API call limits
**Solution**:
- Reduce sync frequency
- Increase cache duration
- Enable auto fallback to distribute calls
- Monitor API usage
- Consider upgrading subscription tier

### Issue: Real-time tracking not working
**Solution**:
- Verify "Enable Real-time Tracking" is checked
- Check provider supports real-time tracking
- Verify API key has real-time tracking permissions
- Check network connectivity

## Security Considerations

- **API Keys**: Store API keys securely and never share them
- **Test Mode**: Always use test mode for initial testing
- **Debug Logging**: Disable debug logging in production to avoid exposing sensitive information
- **Rate Limits**: Monitor API usage to prevent unexpected charges

## Related Documents

- **Flight Schedule**: Uses settings for data synchronization
- **Master Air Waybill**: Uses settings for flight information updates
- **Air Shipment**: Uses settings for flight tracking

## Next Steps

- Review [Setup Guide](setup.md) for initial configuration
- Learn about [Flight Schedule](master-data.md#flight-schedule) management
- Understand [Master Air Waybill](master-air-waybill.md) operations

---

*For detailed setup instructions, refer to the [Setup Guide](setup.md).*

