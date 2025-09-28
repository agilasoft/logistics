scheduler_events = {
    "cron": {
        "*/2 * * * *": [  # tick every 2 minutes
            "logistics.transport.telematics.jobs.tick",
        ]
    }
}