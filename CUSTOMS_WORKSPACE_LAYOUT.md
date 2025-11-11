# Customs Workspace - Ideal Layout

## Recommended Structure

```
Customs Workspace
│
├── Quick Access (Shortcuts)
│   ├── Sales Quote
│   ├── Declaration
│   ├── Permit Application          [NEW]
│   └── Exemption Certificate       [NEW]
│
├── Master Files & Settings
│   ├── Commodity
│   ├── Customs Authority
│   ├── Permit Type                [NEW]
│   └── Exemption Type             [NEW]
│
├── Permit Management              [NEW CARD]
│   ├── Permit Type
│   └── Permit Application
│
├── Exemption Management           [NEW CARD]
│   ├── Exemption Type
│   └── Exemption Certificate
│
└── Reports & Analytics
    ├── Declaration Status Report
    ├── Declaration Value Report
    ├── Customs Compliance Report
    └── Customs Dashboard
```

---

## Detailed Workspace Configuration

### Shortcuts (Quick Access)
**Purpose**: Most frequently used transactions

1. **Sales Quote**
   - Color: Grey
   - Doc View: List
   - Type: DocType

2. **Declaration**
   - Color: Blue (or Grey)
   - Doc View: List
   - Type: DocType

3. **Permit Application** [NEW]
   - Color: Orange
   - Doc View: List
   - Type: DocType
   - Stats Filter: `[["Permit Application","status","=","Draft",false]]`

4. **Exemption Certificate** [NEW]
   - Color: Green
   - Doc View: List
   - Type: DocType
   - Stats Filter: `[["Exemption Certificate","status","=","Active",false]]`

---

### Master Files & Settings Card

**Card Name**: "Master Files & Settings"

**Links**:
1. **Commodity**
   - Link To: Commodity
   - Type: DocType

2. **Customs Authority**
   - Link To: Customs Authority
   - Type: DocType

3. **Permit Type** [NEW]
   - Link To: Permit Type
   - Type: DocType

4. **Exemption Type** [NEW]
   - Link To: Exemption Type
   - Type: DocType

5. **Customs Settings**
   - Link To: Customs Settings
   - Type: DocType

---

### Permit Management Card [NEW]

**Card Name**: "Permit Management"

**Links**:
1. **Permit Type**
   - Link To: Permit Type
   - Type: DocType

2. **Permit Application**
   - Link To: Permit Application
   - Type: DocType

**Purpose**: Centralized location for all permit-related activities

---

### Exemption Management Card [NEW]

**Card Name**: "Exemption Management"

**Links**:
1. **Exemption Type**
   - Link To: Exemption Type
   - Type: DocType

2. **Exemption Certificate**
   - Link To: Exemption Certificate
   - Type: DocType

**Purpose**: Centralized location for all exemption-related activities

---

### Reports & Analytics Card

**Card Name**: "Reports & Analytics"

**Links**:
1. **Declaration Status Report**
   - Link To: Declaration Status Report
   - Type: Report
   - Report Ref DocType: Declaration

2. **Declaration Value Report**
   - Link To: Declaration Value Report
   - Type: Report
   - Report Ref DocType: Declaration

3. **Customs Compliance Report**
   - Link To: Customs Compliance Report
   - Type: Report
   - Report Ref DocType: Declaration

4. **Customs Dashboard**
   - Link To: Customs Dashboard
   - Type: Report
   - Report Ref DocType: Declaration

---

## JSON Structure for Workspace

### Shortcuts Array
```json
"shortcuts": [
  {
    "color": "Grey",
    "doc_view": "List",
    "label": "Sales Quote",
    "link_to": "Sales Quote",
    "stats_filter": "[]",
    "type": "DocType"
  },
  {
    "color": "Grey",
    "doc_view": "List",
    "label": "Declaration",
    "link_to": "Declaration",
    "stats_filter": "[]",
    "type": "DocType"
  },
  {
    "color": "Orange",
    "doc_view": "List",
    "label": "Permit Application",
    "link_to": "Permit Application",
    "stats_filter": "[[\"Permit Application\",\"status\",\"=\",\"Draft\",false]]",
    "type": "DocType"
  },
  {
    "color": "Green",
    "doc_view": "List",
    "label": "Exemption Certificate",
    "link_to": "Exemption Certificate",
    "stats_filter": "[[\"Exemption Certificate\",\"status\",\"=\",\"Active\",false]]",
    "type": "DocType"
  }
]
```

### Links Array
```json
"links": [
  {
    "type": "Card Break",
    "label": "Master Files & Settings",
    "link_count": 5
  },
  {
    "label": "Commodity",
    "link_to": "Commodity",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Customs Authority",
    "link_to": "Customs Authority",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Permit Type",
    "link_to": "Permit Type",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Exemption Type",
    "link_to": "Exemption Type",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Customs Settings",
    "link_to": "Customs Settings",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "type": "Card Break",
    "label": "Permit Management",
    "link_count": 2
  },
  {
    "label": "Permit Type",
    "link_to": "Permit Type",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Permit Application",
    "link_to": "Permit Application",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "type": "Card Break",
    "label": "Exemption Management",
    "link_count": 2
  },
  {
    "label": "Exemption Type",
    "link_to": "Exemption Type",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "label": "Exemption Certificate",
    "link_to": "Exemption Certificate",
    "type": "Link",
    "link_type": "DocType"
  },
  {
    "type": "Card Break",
    "label": "Reports & Analytics",
    "link_count": 4
  },
  {
    "label": "Declaration Status Report",
    "link_to": "Declaration Status Report",
    "type": "Link",
    "link_type": "Report",
    "report_ref_doctype": "Declaration"
  },
  {
    "label": "Declaration Value Report",
    "link_to": "Declaration Value Report",
    "type": "Link",
    "link_type": "Report",
    "report_ref_doctype": "Declaration"
  },
  {
    "label": "Customs Compliance Report",
    "link_to": "Customs Compliance Report",
    "type": "Link",
    "link_type": "Report",
    "report_ref_doctype": "Declaration"
  },
  {
    "label": "Customs Dashboard",
    "link_to": "Customs Dashboard",
    "type": "Link",
    "link_type": "Report",
    "report_ref_doctype": "Declaration"
  }
]
```

---

## Visual Layout

```
┌─────────────────────────────────────────────────────────┐
│                    CUSTOMS WORKSPACE                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  QUICK ACCESS                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Sales   │  │Declaration│  │  Permit │  │Exemption │ │
│  │  Quote   │  │           │  │  App    │  │Cert      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  MASTER FILES & SETTINGS                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ • Commodity                                          │ │
│  │ • Customs Authority                                  │ │
│  │ • Permit Type                                        │ │
│  │ • Exemption Type                                     │ │
│  │ • Customs Settings                                   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  PERMIT MANAGEMENT                                        │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ • Permit Type                                        │ │
│  │ • Permit Application                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  EXEMPTION MANAGEMENT                                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ • Exemption Type                                     │ │
│  │ • Exemption Certificate                              │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  REPORTS & ANALYTICS                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ • Declaration Status Report                         │ │
│  │ • Declaration Value Report                          │ │
│  │ • Customs Compliance Report                         │ │
│  │ • Customs Dashboard                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Color Coding Recommendations

### Shortcuts
- **Sales Quote**: Grey (neutral)
- **Declaration**: Blue (primary transaction)
- **Permit Application**: Orange (attention/action needed)
- **Exemption Certificate**: Green (benefit/positive)

### Rationale
- **Grey**: Standard/neutral items
- **Blue**: Primary transactions
- **Orange**: Items requiring attention (draft permits)
- **Green**: Active/beneficial items (active exemptions)

---

## Organization Principles

1. **Quick Access**: Most frequently used transactions
2. **Master Files**: Reference data grouped together
3. **Functional Groups**: Related items grouped by function (Permits, Exemptions)
4. **Reports**: All reports in one section for easy access

---

## Benefits of This Layout

1. **Clear Hierarchy**: Quick access for daily tasks, detailed sections for management
2. **Logical Grouping**: Related items grouped together
3. **Easy Navigation**: Users can quickly find what they need
4. **Scalable**: Easy to add new items in appropriate sections
5. **Consistent**: Follows Frappe workspace best practices

---

## Implementation Steps

1. Go to **Workspace** → **Customs**
2. Click **Customize**
3. Add new shortcuts:
   - Permit Application
   - Exemption Certificate
4. Add to Master Files:
   - Permit Type
   - Exemption Type
5. Create new cards:
   - Permit Management
   - Exemption Management
6. Add links to each card
7. Save

---

## Notes

- **Child tables** (Permit Requirement, Declaration Exemption) don't need workspace entries - accessed via parent DocTypes
- **Declaration** already exists - will automatically show new Permits and Exemptions tabs
- Consider adding **Number Cards** for:
  - Pending Permit Applications
  - Active Exemption Certificates
  - Draft Declarations
  - Approved Declarations

---

**Last Updated**: 2025-01-27  
**Status**: Ready for Implementation

