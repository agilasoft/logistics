# Logistics App - Workspace Layout

## 📁 Root Structure

```
logistics/
├── frontend/                          # Frontend application (Vue.js)
├── logistics/                         # Backend Python modules
├── docs/                              # Documentation
├── hooks.py                           # Frappe hooks
├── pyproject.toml                      # Python project config
├── requirements.txt                   # Python dependencies
└── README.md
```

---

## 🎨 Frontend Structure (`frontend/`)

```
frontend/
├── index.html                         # Entry HTML file
├── package.json                       # Node.js dependencies
├── vite.config.js                     # Vite configuration
├── tailwind.config.js                 # Tailwind CSS config
├── postcss.config.js                  # PostCSS config
├── yarn.lock                           # Dependency lock file
├── node_modules/                      # Node dependencies
│
├── public/                            # Static assets
│
└── src/                               # Source code
    ├── main.js                        # Application entry point
    ├── App.vue                        # Root Vue component
    ├── index.css                      # Global styles
    ├── router.js                      # Vue Router configuration
    │
    ├── assets/                        # Images, fonts, etc.
    │
    └── pages/                         # Page components
        └── Home.vue                   # Home page
```

### 📝 Frontend Technology Stack
- **Framework**: Vue 3
- **Router**: Vue Router 4
- **UI Library**: Frappe UI
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Icons**: Feather Icons

### ➕ Where to Add New Frontend Components

#### For Customs Module Pages:
```
frontend/src/pages/
├── Home.vue                           # Existing
├── customs/                           # NEW - Create this directory
│   ├── DeclarationList.vue           # NEW - Declaration list page
│   ├── DeclarationForm.vue           # NEW - Declaration form page
│   ├── PermitApplicationList.vue     # NEW - Permit applications list
│   ├── PermitApplicationForm.vue      # NEW - Permit application form
│   ├── ExemptionCertificateList.vue  # NEW - Exemption certificates list
│   ├── ExemptionCertificateForm.vue  # NEW - Exemption certificate form
│   └── CustomsDashboard.vue          # NEW - Customs dashboard
```

#### For Custom Components:
```
frontend/src/components/               # NEW - Create this directory
├── customs/                           # NEW - Customs-specific components
│   ├── PermitRequirementCard.vue      # NEW - Permit requirement card
│   ├── ExemptionCard.vue              # NEW - Exemption card
│   ├── DeclarationStatusBadge.vue     # NEW - Status badge
│   ├── PermitStatusBadge.vue          # NEW - Permit status badge
│   └── ExemptionCalculator.vue        # NEW - Exemption calculator
```

#### Update Router:
```javascript
// frontend/src/router.js
// Add routes for new pages:
{
  path: '/customs/declarations',
  name: 'DeclarationList',
  component: () => import('@/pages/customs/DeclarationList.vue'),
},
{
  path: '/customs/declarations/:id',
  name: 'DeclarationForm',
  component: () => import('@/pages/customs/DeclarationForm.vue'),
},
{
  path: '/customs/permits',
  name: 'PermitApplicationList',
  component: () => import('@/pages/customs/PermitApplicationList.vue'),
},
// ... etc
```

---

## 🐍 Backend Structure (`logistics/`)

```
logistics/
├── __init__.py
├── customs/                           # Customs module
│   ├── __init__.py
│   │
│   ├── doctype/                       # DocType definitions
│   │   ├── __init__.py
│   │   │
│   │   ├── declaration/              # Declaration DocType
│   │   │   ├── declaration.json
│   │   │   ├── declaration.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── permit_type/              # ✅ NEW - Permit Type
│   │   │   ├── permit_type.json
│   │   │   ├── permit_type.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── permit_application/       # ✅ NEW - Permit Application
│   │   │   ├── permit_application.json
│   │   │   ├── permit_application.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── permit_requirement/       # ✅ NEW - Permit Requirement
│   │   │   ├── permit_requirement.json
│   │   │   └── __init__.py
│   │   │
│   │   ├── permit_type_commodity/    # ✅ NEW - Child table
│   │   ├── permit_type_country/      # ✅ NEW - Child table
│   │   ├── permit_application_attachment/ # ✅ NEW - Child table
│   │   │
│   │   ├── exemption_type/           # ✅ NEW - Exemption Type
│   │   │   ├── exemption_type.json
│   │   │   ├── exemption_type.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── exemption_certificate/    # ✅ NEW - Exemption Certificate
│   │   │   ├── exemption_certificate.json
│   │   │   ├── exemption_certificate.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── declaration_exemption/     # ✅ NEW - Declaration Exemption
│   │   │   ├── declaration_exemption.json
│   │   │   ├── declaration_exemption.py
│   │   │   └── __init__.py
│   │   │
│   │   ├── exemption_certificate_declaration/ # ✅ NEW - Child table
│   │   ├── exemption_certificate_attachment/   # ✅ NEW - Child table
│   │   │
│   │   ├── commodity/                # Existing
│   │   ├── commodities/              # Existing
│   │   ├── declaration_commodity/    # Existing
│   │   ├── declaration_charges/      # Existing
│   │   ├── declaration_document/     # Existing
│   │   ├── customs_settings/         # Existing
│   │   └── other_commodity_code/     # Existing
│   │
│   ├── report/                       # Reports
│   │   ├── declaration_status_report/
│   │   ├── declaration_value_report/
│   │   ├── customs_compliance_report/
│   │   └── customs_dashboard/
│   │
│   └── workspace/                    # Workspace definitions
│       └── customs/
│           └── customs.json
│
├── logistics/                        # Other logistics modules
│   ├── doctype/
│   │   ├── customs_authority/
│   │   ├── load_type/
│   │   ├── transport_mode/
│   │   └── ...
│   └── ...
│
└── [other modules]/                  # Other app modules
```

---

## 📋 New DocTypes Created (Backend)

### ✅ Permit Management
1. **Permit Type** - Master data for permit types
2. **Permit Application** - Transaction for permit applications
3. **Permit Requirement** - Child table for Declaration
4. **Permit Type Commodity** - Child table for Permit Type
5. **Permit Type Country** - Child table for Permit Type
6. **Permit Application Attachment** - Child table for Permit Application

### ✅ Exemption Management
1. **Exemption Type** - Master data for exemption types
2. **Exemption Certificate** - Transaction for exemption certificates
3. **Declaration Exemption** - Child table for Declaration
4. **Exemption Certificate Declaration** - Child table for Exemption Certificate
5. **Exemption Certificate Attachment** - Child table for Exemption Certificate

### ✅ Enhanced Declaration
- Added **Permits** tab with `permit_requirements` child table
- Added **Exemptions** tab with `exemptions` child table
- Enhanced Python class with exemption calculation and permit validation

---

## 🎯 Frontend Integration Points

### API Endpoints to Use (Frappe Framework)

All DocTypes are automatically exposed via Frappe's REST API:

```
# Base URL: /api/resource/

# Permit Management
GET    /api/resource/Permit Type
POST   /api/resource/Permit Type
GET    /api/resource/Permit Application
POST   /api/resource/Permit Application
GET    /api/resource/Permit Application/{name}

# Exemption Management
GET    /api/resource/Exemption Type
POST   /api/resource/Exemption Type
GET    /api/resource/Exemption Certificate
POST   /api/resource/Exemption Certificate
GET    /api/resource/Exemption Certificate/{name}

# Declaration (Enhanced)
GET    /api/resource/Declaration
POST   /api/resource/Declaration
GET    /api/resource/Declaration/{name}
POST   /api/resource/Declaration/{name}/submit
```

### Custom API Methods (if needed)

You can add custom API methods in the Python files:

```python
# In permit_application.py or declaration.py
@frappe.whitelist()
def get_permit_status(permit_application):
    # Custom logic
    pass

@frappe.whitelist()
def calculate_exemption_amount(declaration, exemption_type):
    # Custom calculation
    pass
```

---

## 📱 Suggested Frontend Pages Structure

### 1. Declaration Management
```
pages/customs/
├── DeclarationList.vue        # List view with filters
├── DeclarationForm.vue         # Form with tabs:
│                               # - Basic Info
│                               # - Commodities
│                               # - Transport
│                               # - Permits (NEW)
│                               # - Exemptions (NEW)
│                               # - Documents
│                               # - Charges
└── DeclarationDetail.vue       # Read-only detail view
```

### 2. Permit Management
```
pages/customs/
├── PermitApplicationList.vue   # List with status filters
├── PermitApplicationForm.vue   # Form for creating/editing
└── PermitTypeList.vue          # Master data list
```

### 3. Exemption Management
```
pages/customs/
├── ExemptionCertificateList.vue # List with filters
├── ExemptionCertificateForm.vue # Form for certificates
└── ExemptionTypeList.vue        # Master data list
```

### 4. Dashboard
```
pages/customs/
└── CustomsDashboard.vue         # Overview with:
                                  # - Pending permits
                                  # - Expiring certificates
                                  # - Declaration status summary
                                  # - Compliance metrics
```

---

## 🔧 Configuration Files

### Frontend Config
- `vite.config.js` - Vite build configuration
- `tailwind.config.js` - Tailwind CSS customization
- `package.json` - Dependencies and scripts

### Backend Config
- `hooks.py` - Frappe hooks for app initialization
- `pyproject.toml` - Python package configuration

---

## 📚 Documentation Files

```
Root/
├── CUSTOMS_DOCTYPE_ENHANCEMENTS.md    # Design document
├── CUSTOMS_MODULE_ANALYSIS.md          # Analysis document
├── DECLARATION_ENHANCEMENTS.md         # Declaration enhancements
├── IMPLEMENTATION_SUMMARY.md           # Implementation summary
└── WORKSPACE_LAYOUT.md                 # This file
```

---

## 🚀 Next Steps for Frontend Development

1. **Create page components** in `frontend/src/pages/customs/`
2. **Create reusable components** in `frontend/src/components/customs/`
3. **Update router** in `frontend/src/router.js` with new routes
4. **Use Frappe UI components** for forms and lists
5. **Connect to API** using Frappe's resource methods
6. **Add navigation** to workspace or menu

---

## 📝 Notes

- All backend DocTypes are ready and functional
- Frontend uses Vue 3 with Frappe UI
- API endpoints are automatically available via Frappe framework
- No additional backend setup needed for frontend development
- Follow Frappe UI patterns for consistency

---

**Last Updated**: 2025-01-27  
**Status**: Backend complete, Frontend ready for development

