# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_warehousing_main_guide():
    """Create the main warehousing documentation page"""
    
    print("📚 Creating main warehousing documentation...")
    
    # Create main warehousing guide web page
    if not frappe.db.exists("Web Page", "warehousing-main-guide"):
        main_guide = frappe.get_doc({
            "doctype": "Web Page",
            "title": "Warehousing Module - Complete User Guide",
            "route": "/wiki/space/warehousing/warehousing-main-guide",
            "published": 1,
            "content_type": "HTML",
            "main_section": '''
            <div class="warehousing-guide-container">
                <div class="guide-header">
                    <h1>🏭 CargoNext Warehousing Module</h1>
                    <p class="subtitle">Complete User Guide for Warehouse Management Operations</p>
                    <div class="guide-badges">
                        <span class="badge">Warehouse Management</span>
                        <span class="badge">Inventory Control</span>
                        <span class="badge">Value-Added Services</span>
                        <span class="badge">Sustainability Tracking</span>
                    </div>
                </div>

                <div class="guide-overview">
                    <h2>📋 Module Overview</h2>
                    <p>The CargoNext Warehousing Module provides comprehensive warehouse management capabilities including:</p>
                    <ul class="feature-list">
                        <li><strong>Warehouse Job Management</strong> - Complete lifecycle management of warehouse operations</li>
                        <li><strong>Storage Location Management</strong> - Organized storage with capacity tracking</li>
                        <li><strong>Handling Unit Tracking</strong> - Track items through various handling units</li>
                        <li><strong>Value-Added Services (VAS)</strong> - Manage additional services like packaging, labeling</li>
                        <li><strong>Periodic Billing</strong> - Automated billing based on storage and services</li>
                        <li><strong>Capacity Management</strong> - Real-time capacity monitoring and alerts</li>
                        <li><strong>Sustainability Dashboard</strong> - Track carbon footprint and environmental impact</li>
                    </ul>
                </div>

                <div class="guide-navigation">
                    <h2>📖 Documentation Sections</h2>
                    <div class="nav-grid">
                        <div class="nav-card">
                            <h3>🔧 Setup & Configuration</h3>
                            <ul>
                                <li><a href="/wiki/space/warehousing/warehouse-settings">Warehouse Settings</a></li>
                                <li><a href="/wiki/space/warehousing/storage-locations">Storage Locations</a></li>
                                <li><a href="/wiki/space/warehousing/handling-unit-types">Handling Unit Types</a></li>
                                <li><a href="/wiki/space/warehousing/storage-types">Storage Types</a></li>
                            </ul>
                        </div>
                        
                        <div class="nav-card">
                            <h3>📦 Operations</h3>
                            <ul>
                                <li><a href="/wiki/space/warehousing/warehouse-jobs">Warehouse Jobs</a></li>
                                <li><a href="/wiki/space/warehousing/vas-operations">VAS Operations</a></li>
                                <li><a href="/wiki/space/warehousing/inbound-operations">Inbound Operations</a></li>
                                <li><a href="/wiki/space/warehousing/outbound-operations">Outbound Operations</a></li>
                            </ul>
                        </div>
                        
                        <div class="nav-card">
                            <h3>💰 Billing & Contracts</h3>
                            <ul>
                                <li><a href="/wiki/space/warehousing/warehouse-contracts">Warehouse Contracts</a></li>
                                <li><a href="/wiki/space/warehousing/periodic-billing">Periodic Billing</a></li>
                                <li><a href="/wiki/space/warehousing/charges-management">Charges Management</a></li>
                            </ul>
                        </div>
                        
                        <div class="nav-card">
                            <h3>📊 Reports & Analytics</h3>
                            <ul>
                                <li><a href="/wiki/space/warehousing/warehouse-dashboard">Warehouse Dashboard</a></li>
                                <li><a href="/wiki/space/warehousing/sustainability-reports">Sustainability Reports</a></li>
                                <li><a href="/wiki/space/warehousing/capacity-reports">Capacity Reports</a></li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="quick-start">
                    <h2>🚀 Quick Start Guide</h2>
                    <div class="steps-container">
                        <div class="step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <h4>Configure Warehouse Settings</h4>
                                <p>Set up your warehouse parameters, billing options, and capacity management settings.</p>
                                <a href="/wiki/space/warehousing/warehouse-settings" class="btn-link">Configure Settings →</a>
                            </div>
                        </div>
                        
                        <div class="step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <h4>Create Storage Locations</h4>
                                <p>Define your warehouse layout with storage locations, zones, and capacity limits.</p>
                                <a href="/wiki/space/warehousing/storage-locations" class="btn-link">Setup Locations →</a>
                            </div>
                        </div>
                        
                        <div class="step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <h4>Define Handling Unit Types</h4>
                                <p>Configure different types of handling units (pallets, containers, boxes) with their specifications.</p>
                                <a href="/wiki/space/warehousing/handling-unit-types" class="btn-link">Setup Units →</a>
                            </div>
                        </div>
                        
                        <div class="step">
                            <div class="step-number">4</div>
                            <div class="step-content">
                                <h4>Create Your First Warehouse Job</h4>
                                <p>Start managing warehouse operations with inbound, outbound, or transfer jobs.</p>
                                <a href="/wiki/space/warehousing/warehouse-jobs" class="btn-link">Create Job →</a>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="key-features">
                    <h2>✨ Key Features</h2>
                    <div class="features-grid">
                        <div class="feature-card">
                            <div class="feature-icon">📦</div>
                            <h4>Inventory Management</h4>
                            <p>Track items across multiple storage locations with real-time visibility</p>
                        </div>
                        
                        <div class="feature-card">
                            <div class="feature-icon">🔄</div>
                            <h4>Workflow Automation</h4>
                            <p>Automated workflows for inbound, outbound, and transfer operations</p>
                        </div>
                        
                        <div class="feature-card">
                            <div class="feature-icon">💰</div>
                            <h4>Automated Billing</h4>
                            <p>Periodic billing based on storage duration, volume, and services</p>
                        </div>
                        
                        <div class="feature-card">
                            <div class="feature-icon">📊</div>
                            <h4>Capacity Management</h4>
                            <p>Real-time capacity monitoring with alerts and optimization suggestions</p>
                        </div>
                        
                        <div class="feature-card">
                            <div class="feature-icon">🌱</div>
                            <h4>Sustainability Tracking</h4>
                            <p>Track carbon footprint and environmental impact of warehouse operations</p>
                        </div>
                        
                        <div class="feature-card">
                            <div class="feature-icon">⚙️</div>
                            <h4>Value-Added Services</h4>
                            <p>Manage additional services like packaging, labeling, and quality control</p>
                        </div>
                    </div>
                </div>

                <div class="troubleshooting">
                    <h2>🔧 Common Issues & Solutions</h2>
                    <div class="issue-list">
                        <div class="issue-item">
                            <h4>Q: How do I set up storage locations?</h4>
                            <p>A: Use the Storage Location Configurator to define your warehouse layout. See our <a href="/wiki/space/warehousing/storage-locations">Storage Locations Guide</a> for detailed steps.</p>
                        </div>
                        
                        <div class="issue-item">
                            <h4>Q: How does periodic billing work?</h4>
                            <p>A: Periodic billing automatically calculates charges based on storage duration, volume, and services. Check our <a href="/wiki/space/warehousing/periodic-billing">Periodic Billing Guide</a> for configuration details.</p>
                        </div>
                        
                        <div class="issue-item">
                            <h4>Q: How do I track handling units?</h4>
                            <p>A: Handling units are tracked through the Warehouse Job system. See our <a href="/wiki/space/warehousing/handling-unit-types">Handling Unit Types Guide</a> for setup instructions.</p>
                        </div>
                    </div>
                </div>

                <div class="support-info">
                    <h2>🆘 Need Help?</h2>
                    <p>If you need additional assistance with the Warehousing Module:</p>
                    <ul>
                        <li>📧 Contact Support: support@cargonext.io</li>
                        <li>📚 Browse all documentation in this space</li>
                        <li>💬 Join our community forum</li>
                        <li>🎓 Attend our training sessions</li>
                    </ul>
                </div>
            </div>

            <style>
                .warehousing-guide-container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                
                .guide-header {
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 40px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 15px;
                }
                
                .guide-header h1 {
                    font-size: 2.5em;
                    margin: 0 0 10px 0;
                    font-weight: 700;
                }
                
                .subtitle {
                    font-size: 1.2em;
                    margin: 0 0 20px 0;
                    opacity: 0.9;
                }
                
                .guide-badges {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    flex-wrap: wrap;
                }
                
                .badge {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: 500;
                }
                
                .guide-overview, .guide-navigation, .quick-start, .key-features, .troubleshooting, .support-info {
                    margin-bottom: 40px;
                    padding: 30px;
                    background: #f8f9fa;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }
                
                .guide-overview h2, .guide-navigation h2, .quick-start h2, .key-features h2, .troubleshooting h2, .support-info h2 {
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 1.8em;
                }
                
                .feature-list {
                    list-style: none;
                    padding: 0;
                }
                
                .feature-list li {
                    padding: 10px 0;
                    border-bottom: 1px solid #e9ecef;
                }
                
                .nav-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                }
                
                .nav-card {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                
                .nav-card h3 {
                    color: #667eea;
                    margin-bottom: 15px;
                }
                
                .nav-card ul {
                    list-style: none;
                    padding: 0;
                }
                
                .nav-card li {
                    padding: 5px 0;
                }
                
                .nav-card a {
                    color: #667eea;
                    text-decoration: none;
                    font-weight: 500;
                }
                
                .nav-card a:hover {
                    text-decoration: underline;
                }
                
                .steps-container {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                
                .step {
                    display: flex;
                    align-items: flex-start;
                    gap: 20px;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                
                .step-number {
                    background: #667eea;
                    color: white;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    flex-shrink: 0;
                }
                
                .step-content h4 {
                    margin: 0 0 10px 0;
                    color: #333;
                }
                
                .btn-link {
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-size: 0.9em;
                    margin-top: 10px;
                }
                
                .btn-link:hover {
                    background: #5a6fd8;
                    text-decoration: none;
                    color: white;
                }
                
                .features-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }
                
                .feature-card {
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                    text-align: center;
                }
                
                .feature-icon {
                    font-size: 2.5em;
                    margin-bottom: 15px;
                }
                
                .feature-card h4 {
                    color: #333;
                    margin-bottom: 10px;
                }
                
                .issue-list {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                
                .issue-item {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                
                .issue-item h4 {
                    color: #667eea;
                    margin-bottom: 10px;
                }
                
                .support-info ul {
                    list-style: none;
                    padding: 0;
                }
                
                .support-info li {
                    padding: 8px 0;
                    border-bottom: 1px solid #e9ecef;
                }
                
                @media (max-width: 768px) {
                    .nav-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .features-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .step {
                        flex-direction: column;
                        text-align: center;
                    }
                }
            </style>
            ''',
            "meta_title": "Warehousing Module - Complete User Guide",
            "meta_description": "Comprehensive user guide for CargoNext Warehousing Module including setup, operations, and best practices"
        })
        main_guide.insert(ignore_permissions=True)
        print("✅ Main warehousing guide created")
    else:
        print("ℹ️ Main warehousing guide already exists")
    
    frappe.db.commit()


if __name__ == "__main__":
    create_warehousing_main_guide()

