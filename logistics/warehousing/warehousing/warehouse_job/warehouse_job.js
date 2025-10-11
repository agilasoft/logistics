// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job', {
    refresh: function(frm) {
        // Always add a test button to verify Actions menu is working
        frm.add_custom_button(__('Test Button'), function() {
            frappe.msgprint(__('Actions menu is working! Doc Status: {0}', [frm.doc.docstatus]));
        }, __('Actions'));
        
        // Add custom buttons for dashboard actions
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Refresh Dashboard'), function() {
                frm.reload_doc();
            }, __('Actions'));
            
            frm.add_custom_button(__('Full Screen Dashboard'), function() {
                frm.open_dashboard_fullscreen();
            }, __('Actions'));
        }
        
        // Add Gate Pass creation buttons - show for submitted jobs
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Gate Passes'), function() {
                if (frm.doc.docks && frm.doc.docks.length > 0) {
                    frm.create_gate_passes_for_all_docks();
                } else {
                    frappe.msgprint(__('No docking entries found. Please add docking entries first.'));
                }
            }, __('Actions'));
            
            frm.add_custom_button(__('View Gate Passes'), function() {
                frm.view_related_gate_passes();
            }, __('Actions'));
        }
        
        // Add individual dock gate pass creation buttons
        if (frm.doc.docstatus === 1 && frm.fields_dict.docks) {
            frm.fields_dict.docks.grid.add_custom_button(__('Create Gate Pass'), function() {
                if (frm.doc.docks && frm.doc.docks.length > 0) {
                    frappe.confirm(
                        __('Create Gate Pass for all {0} dock{1}?', [
                            frm.doc.docks.length, 
                            frm.doc.docks.length > 1 ? 's' : ''
                        ]),
                        function() {
                            frm.doc.docks.forEach(function(row) {
                                frm.create_gate_pass_for_dock(row);
                            });
                        }
                    );
                } else {
                    frappe.msgprint(__('No docking entries found. Please add docking entries first.'));
                }
            }, __('Actions'));
        }
    },


    onload: function(frm) {
        // Initialize dashboard when the form loads
        if (frm.doc.warehouse_job_html) {
            frm.setup_dashboard_interactions();
        }
    },

    setup_dashboard_interactions: function(frm) {
        // Wait for the HTML field to be rendered
        setTimeout(() => {
            const dashboardContainer = frm.fields_dict.warehouse_job_html.$wrapper.find('.dashboard-container');
            if (dashboardContainer.length) {
                frm.enhance_dashboard_functionality(dashboardContainer);
            }
        }, 1000);
    },

    enhance_dashboard_functionality: function(frm, container) {
        // Add real-time updates
        frm.setup_dashboard_auto_refresh(container);
        
        // Add keyboard shortcuts
        frm.setup_dashboard_keyboard_shortcuts(container);
        
        // Add search functionality
        frm.setup_dashboard_search(container);
    },

    setup_dashboard_auto_refresh: function(frm, container) {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (container.is(':visible')) {
                frm.refresh_dashboard_data();
            }
        }, 30000);
    },

    setup_dashboard_keyboard_shortcuts: function(frm, container) {
        container.on('keydown', (e) => {
            // Ctrl+R to refresh dashboard
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                frm.refresh_dashboard_data();
            }
            
            // Escape to clear selections
            if (e.key === 'Escape') {
                frm.clear_dashboard_selections();
            }
        });
    },

    setup_dashboard_search: function(frm, container) {
        // Add search input
        const searchHtml = `
            <div class="dashboard-search" style="margin-bottom: 15px;">
                <input type="text" id="dashboard-search" placeholder="Search handling units or locations..." 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
            </div>
        `;
        
        container.find('.left-panel .section:first').prepend(searchHtml);
        
        // Setup search functionality
        container.find('#dashboard-search').on('input', (e) => {
            frm.filter_dashboard_items(e.target.value);
        });
    },

    refresh_dashboard_data: function(frm) {
        // Reload the dashboard HTML
        frm.reload_doc();
    },

    filter_dashboard_items: function(frm, searchTerm) {
        const term = searchTerm.toLowerCase();
        
        // Filter handling units
        frm.fields_dict.warehouse_job_html.$wrapper.find('.handling-unit-card').each(function() {
            const card = $(this);
            const huName = card.find('.hu-name').text().toLowerCase();
            const huType = card.find('.hu-info-item').first().find('.hu-info-value').text().toLowerCase();
            
            if (huName.includes(term) || huType.includes(term)) {
                card.show();
            } else {
                card.hide();
            }
        });
        
        // Filter locations in map
        frm.fields_dict.warehouse_job_html.$wrapper.find('.map-location').each(function() {
            const location = $(this);
            const locationText = location.text().toLowerCase();
            
            if (locationText.includes(term)) {
                location.show();
            } else {
                location.hide();
            }
        });
    },

    clear_dashboard_selections: function(frm) {
        // Clear handling unit selections
        frm.fields_dict.warehouse_job_html.$wrapper.find('.handling-unit-card.selected').removeClass('selected');
        
        // Clear location selections
        frm.fields_dict.warehouse_job_html.$wrapper.find('.map-location.selected').removeClass('selected');
        
        // Clear details panel
        frm.fields_dict.warehouse_job_html.$wrapper.find('.location-details').removeClass('show').html('<p>Select a location from the map to view details.</p>');
    },

    open_dashboard_fullscreen: function(frm) {
        // Open dashboard in a new window/tab
        const dashboardUrl = `/app/warehouse-job/${frm.doc.name}`;
        window.open(dashboardUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
    },

});

// Extend the Warehouse Job form with Gate Pass methods
frappe.ui.form.on('Warehouse Job', {
    onload: function(frm) {
        // Add gate pass methods to the form
        frm.create_gate_pass_for_dock = function(dockRow) {
            // Create gate pass for a specific dock entry
            frappe.call({
                method: 'logistics.warehousing.doctype.gate_pass.gate_pass.create_gate_pass_for_docking',
                args: {
                    warehouse_job: frm.doc.name,
                    dock_name: dockRow.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__('Created Gate Pass: {0}', [r.message]));
                        frm.reload_doc();
                    }
                },
                freeze: true,
                freeze_message: __('Creating Gate Pass...')
            });
        };

        frm.create_gate_passes_for_all_docks = function() {
            // Create gate passes for all docking entries
            frappe.confirm(
                __('Create Gate Passes for all {0} docking entries?', [frm.doc.docks.length]),
                function() {
                    frappe.call({
                        method: 'logistics.warehousing.doctype.gate_pass.gate_pass.create_gate_pass_for_docking',
                        args: {
                            warehouse_job: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message) {
                                const gatePasses = Array.isArray(r.message) ? r.message : [r.message];
                                frappe.msgprint(__('Created {0} Gate Pass{1}: {2}', [
                                    gatePasses.length,
                                    gatePasses.length > 1 ? 'es' : '',
                                    gatePasses.join(', ')
                                ]));
                                frm.reload_doc();
                            }
                        },
                        freeze: true,
                        freeze_message: __('Creating Gate Passes...')
                    });
                }
            );
        };

        frm.view_related_gate_passes = function() {
            // View gate passes related to this warehouse job
            frappe.route_options = {
                warehouse_job: frm.doc.name
            };
            frappe.set_route('List', 'Gate Pass');
        };
    }
});

// Global dashboard functions for the HTML template
window.dashboard = {
    toggleHuItems: function(huId) {
        const itemsList = document.getElementById(`hu-items-${huId}`);
        const toggleBtn = itemsList.previousElementSibling;
        
        if (itemsList.classList.contains('show')) {
            itemsList.classList.remove('show');
            toggleBtn.textContent = `Show Items (${toggleBtn.textContent.match(/\d+/)[0]})`;
            toggleBtn.classList.remove('expanded');
        } else {
            itemsList.classList.add('show');
            toggleBtn.textContent = 'Hide Items';
            toggleBtn.classList.add('expanded');
        }
    },

    selectLocation: function(locationPath) {
        // Remove previous selection
        document.querySelectorAll('.map-location').forEach(loc => {
            loc.classList.remove('selected');
        });

        // Add selection to clicked location
        const selectedLocation = document.querySelector(`[data-location="${locationPath}"]`);
        if (selectedLocation) {
            selectedLocation.classList.add('selected');
        }

        // Load location details
        this.loadLocationDetails(locationPath);
    },

    loadLocationDetails: function(locationPath) {
        // This would be implemented in the HTML template
        console.log('Loading details for location:', locationPath);
    }
};
