frappe.listview_settings['Sea Freight Booking'] = {
    get_indicator: function(doc) {
        // Customize color per status
        if (doc.shipping_status === 'Booking Confirmed') {
            return [__('Booking Confirmed'), 'blue', 'shipping_status,=,Booking Confirmed'];
        } else if (doc.shipping_status === 'Loaded on Vessel') {
            return [__('Loaded on Vessel'), 'orange', 'shipping_status,=,Loaded on Vessel'];
        } else if (doc.shipping_status === 'In Transit') {
            return [__('In Transit'), 'purple', 'shipping_status,=,In Transit'];
        } else if (doc.shipping_status === 'Arrived') {
            return [__('Arrived'), 'green', 'shipping_status,=,Arrived'];
        } else if (doc.shipping_status === 'Delivered') {
            return [__('Delivered'), 'darkgreen', 'shipping_status,=,Delivered'];
        } else if (doc.shipping_status === 'Delayed') {
            return [__('Delayed'), 'red', 'shipping_status,=,Delayed'];
        } else {
            return [__(doc.shipping_status || 'Unknown'), 'gray', 'shipping_status,=,' + (doc.shipping_status || '')];
        }
    }
};
