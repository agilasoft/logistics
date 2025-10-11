frappe.pages['plate_scanner'].on_page_load = function(wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Plate Scanner"),
    single_column: true
  });

  new PlateScannerPage(wrapper);
};

class PlateScannerPage {
  constructor(wrapper) {
    this.wrapper = $(wrapper);
    this.make();
    this.bind_events();
  }

  make() {
    this.wrapper.html(`
      <div class="ps-container">
        <div class="ps-header">
          <div class="ps-header-main">
            <div class="ps-header-left">
              <h1>PLATE SCANNER</h1>
              <p>Vehicle Access Control</p>
            </div>
            <div class="ps-header-details">
              <div class="ps-detail-item">
                <label>Status:</label>
                <span id="scanner-status">Ready</span>
              </div>
              <div class="ps-detail-item">
                <label>Last Scan:</label>
                <span id="last-scan">-</span>
              </div>
            </div>
          </div>
        </div>

        <div class="ps-main-content">
          <div class="ps-search-section">
            <div class="ps-search-form">
              <input type="text" id="plate-input" placeholder="Enter plate number (e.g., ABC123)">
              <button id="search-btn">Search</button>
            </div>
          </div>

          <div class="ps-results-section" id="results">
            <div class="ps-results-content" id="search-results">
              <div class="ps-waiting-state">
                <i class="fa fa-car"></i>
                <h3>Ready to Search</h3>
                <p>Enter a plate number to begin</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    `);

    this.add_styles();
  }

  add_styles() {
    this.wrapper.append(`
      <style>
        .ps-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        
        .ps-header {
          background: #fff;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .ps-header-main {
          display: flex;
          justify-content: space-between;
          padding-bottom: 12px;
          border-bottom: 1px solid #eee;
          margin-bottom: 12px;
        }
        
        .ps-header-left h1 {
          font-size: 24px;
          font-weight: 700;
          color: #007bff;
          margin: 0 0 4px 0;
        }
        
        .ps-header-left p {
          font-size: 14px;
          color: #666;
          margin: 0;
        }
        
        .ps-header-details {
          display: flex;
          gap: 20px;
        }
        
        .ps-detail-item {
          display: flex;
          flex-direction: column;
        }
        
        .ps-detail-item label {
          font-size: 12px;
          color: #666;
          font-weight: 600;
          margin-bottom: 2px;
        }
        
        .ps-detail-item span {
          font-size: 14px;
          color: #000;
          font-weight: 500;
        }
        
        .ps-main-content {
          display: flex;
          gap: 20px;
        }
        
        .ps-search-section {
          width: 350px;
          background: #f8f9fa;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        
        .ps-search-form {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .ps-search-form input {
          padding: 12px 16px;
          font-size: 16px;
          border: 2px solid #ddd;
          border-radius: 6px;
          outline: none;
          transition: border-color 0.3s;
        }
        
        .ps-search-form input:focus {
          border-color: #007bff;
        }
        
        .ps-search-form button {
          padding: 12px 24px;
          font-size: 16px;
          font-weight: 600;
          background: #007bff;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          transition: background-color 0.3s;
        }
        
        .ps-search-form button:hover {
          background: #0056b3;
        }
        
        .ps-results-section {
          flex: 1;
          background: #fff;
          border: 1px solid #ddd;
          border-radius: 8px;
          min-height: 300px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .ps-results-content {
          padding: 24px;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .ps-waiting-state {
          text-align: center;
          color: #666;
        }
        
        .ps-waiting-state i {
          font-size: 48px;
          color: #007bff;
          margin-bottom: 16px;
          display: block;
        }
        
        .ps-waiting-state h3 {
          font-size: 20px;
          font-weight: 600;
          margin: 0 0 8px 0;
          color: #000;
        }
        
        .ps-waiting-state p {
          font-size: 14px;
          margin: 0;
          color: #000;
        }
        
        .ps-results-found {
          width: 100%;
        }
        
        .ps-plate-display {
          background: #f8f9fa;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 20px;
          text-align: center;
        }
        
        .ps-vehicle-type {
          font-size: 16px;
          font-weight: 600;
          color: #333;
          margin-bottom: 8px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .ps-plate-number {
          font-size: 36px;
          font-weight: 700;
          color: #007bff;
          margin-bottom: 8px;
          letter-spacing: 2px;
          text-shadow: 0 2px 4px rgba(0, 123, 255, 0.2);
        }
        
        .ps-access-status {
          font-size: 18px;
          font-weight: 600;
          padding: 8px 16px;
          border-radius: 20px;
          display: inline-block;
        }
        
        .ps-access-status.granted {
          background: #d4edda;
          color: #155724;
        }
        
        .ps-access-status.not-found {
          background: #f8d7da;
          color: #721c24;
        }
        
        .ps-dock-door-info {
          background: #fff;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 16px;
        }
        
        .ps-dock-door-main {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .ps-dock-door-left {
          flex: 1;
        }
        
        .ps-dock-door-name {
          font-size: 18px;
          font-weight: 700;
          color: #007bff;
          margin-bottom: 4px;
        }
        
        .ps-dock-door-location {
          font-size: 14px;
          color: #000;
        }
        
        .ps-dock-door-right {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 8px;
        }
        
        .ps-eta-info {
          text-align: center;
          background: #f8f9fa;
          padding: 8px 12px;
          border-radius: 6px;
          border: 1px solid #ddd;
        }
        
        .ps-eta-label {
          font-size: 10px;
          color: #666;
          font-weight: 600;
          text-transform: uppercase;
          margin-bottom: 2px;
        }
        
        .ps-eta-time {
          font-size: 16px;
          font-weight: 700;
          color: #000;
        }
        
        .ps-status-badge {
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        
        .ps-status-badge.assigned {
          background: #cfe2ff;
          color: #084298;
        }
        
        @media (max-width: 768px) {
          .ps-main-content {
            flex-direction: column;
          }
          
          .ps-search-section {
            width: 100%;
          }
          
          .ps-results-section {
            min-height: 250px;
          }
        }
      </style>
    `);
  }

  bind_events() {
    const searchBtn = document.getElementById('search-btn');
    const plateInput = document.getElementById('plate-input');

    searchBtn.addEventListener('click', () => {
      this.handleSearch();
    });

    plateInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.handleSearch();
      }
    });

    // Focus on input when page loads
    plateInput.focus();
  }

  handleSearch() {
    const plateInput = document.getElementById('plate-input');
    const plateNumber = plateInput.value.trim();
    
    if (!plateNumber) {
      frappe.msgprint(__('Please enter a plate number'));
      plateInput.focus();
      return;
    }
    
    if (plateNumber.length < 3) {
      frappe.msgprint(__('Please enter at least 3 characters'));
      plateInput.focus();
      return;
    }
    
    this.searchPlateNumber(plateNumber);
  }

  clearResults() {
    const searchResults = document.getElementById('search-results');
    const scannerStatus = document.getElementById('scanner-status');
    const lastScan = document.getElementById('last-scan');
    
    searchResults.innerHTML = `
      <div class="ps-waiting-state">
        <i class="fa fa-car"></i>
        <h3>Ready to Search</h3>
        <p>Enter a plate number to begin</p>
      </div>
    `;
    
    scannerStatus.textContent = 'Ready';
    lastScan.textContent = '-';
  }

  async searchPlateNumber(plateNumber) {
    try {
      const result = await frappe.call({
        method: 'logistics.warehousing.plate_scanner.search_plate_number',
        args: {
          plate_no: plateNumber
        }
      });
      
      this.displayResults(plateNumber, result.message || []);
    } catch (error) {
      console.error('Error searching plate number:', error);
      frappe.msgprint(__('Error searching plate number: ') + error.message);
      this.displayResults(plateNumber, []);
    }
  }

  displayResults(plateNumber, data) {
    const searchResults = document.getElementById('search-results');
    const scannerStatus = document.getElementById('scanner-status');
    const lastScan = document.getElementById('last-scan');
    
    // Update header status
    scannerStatus.textContent = data && data.length > 0 ? 'Found' : 'Not Found';
    lastScan.textContent = plateNumber;
    
    // Create results content
    let resultsHTML = '';
    
      if (data && data.length > 0) {
        // Get vehicle type and plate number from first result
        const vehicleType = data[0].vehicle_type || 'TRUCK';
        const dockDoor = data[0].docking || 'N/A';
        const eta = data[0].eta || 'N/A';
        const savedPlateNumber = data[0].plate_no || plateNumber;
        
        // Show granted access with dock door info
        resultsHTML = `
          <div class="ps-results-found">
            <div class="ps-plate-display">
              <div class="ps-vehicle-type">${vehicleType}</div>
              <div class="ps-plate-number">${savedPlateNumber}</div>
              <div class="ps-access-status granted">GRANTED</div>
            </div>
            <div class="ps-dock-door-info">
              <div class="ps-dock-door-main">
                <div class="ps-dock-door-left">
                  <div class="ps-dock-door-name">${dockDoor}</div>
                  <div class="ps-dock-door-location">Warehouse A</div>
                </div>
                <div class="ps-dock-door-right">
                  <div class="ps-eta-info">
                    <div class="ps-eta-label">ETA</div>
                    <div class="ps-eta-time">${eta}</div>
                  </div>
                  <div class="ps-status-badge assigned">Assigned</div>
                </div>
              </div>
            </div>
          </div>
        `;
      } else {
        // Show not found
        resultsHTML = `
          <div class="ps-results-found">
            <div class="ps-plate-display">
              <div class="ps-vehicle-type">UNKNOWN</div>
              <div class="ps-plate-number">${plateNumber}</div>
              <div class="ps-access-status not-found">NOT FOUND</div>
            </div>
            <div style="text-align: center; padding: 20px; color: #000;">
              <p>Vehicle not found in system</p>
            </div>
          </div>
        `;
      }
    
    searchResults.innerHTML = resultsHTML;
  }
}