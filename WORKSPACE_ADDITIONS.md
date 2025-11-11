# Customs Workspace - Manual Additions Guide

## Current Workspace Structure

The Customs workspace currently has:
- **Shortcuts**: Sales Quote, Declaration
- **Master Files Card**: Commodity, Customs Authority

---

## New DocTypes to Add to Workspace

### 1. **Permit Management Section**

#### Add as Shortcuts (Quick Access):
1. **Permit Application**
   - Label: "Permit Application"
   - Link To: "Permit Application"
   - Type: DocType
   - Doc View: List
   - Color: Blue (or your preference)

2. **Permit Type** (Master Data)
   - Label: "Permit Type"
   - Link To: "Permit Type"
   - Type: DocType
   - Doc View: List
   - Color: Grey

#### Add as Links (Under a Card):
Create a new card: **"Permit Management"**

Add these links:
1. **Permit Type**
   - Label: "Permit Type"
   - Link To: "Permit Type"
   - Type: DocType

2. **Permit Application**
   - Label: "Permit Application"
   - Link To: "Permit Application"
   - Type: DocType

---

### 2. **Exemption Management Section**

#### Add as Shortcuts (Quick Access):
1. **Exemption Certificate**
   - Label: "Exemption Certificate"
   - Link To: "Exemption Certificate"
   - Type: DocType
   - Doc View: List
   - Color: Green (or your preference)

2. **Exemption Type** (Master Data)
   - Label: "Exemption Type"
   - Link To: "Exemption Type"
   - Type: DocType
   - Doc View: List
   - Color: Grey

#### Add as Links (Under a Card):
Create a new card: **"Exemption Management"**

Add these links:
1. **Exemption Type**
   - Label: "Exemption Type"
   - Link To: "Exemption Type"
   - Type: DocType

2. **Exemption Certificate**
   - Label: "Exemption Certificate"
   - Link To: "Exemption Certificate"
   - Type: DocType

---

## Recommended Workspace Layout

### Option 1: Organized by Function

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
│   ├── Permit Type                 [NEW]
│   └── Exemption Type              [NEW]
│
├── Permit Management               [NEW CARD]
│   ├── Permit Type
│   └── Permit Application
│
└── Exemption Management            [NEW CARD]
    ├── Exemption Type
    └── Exemption Certificate
```

### Option 2: Grouped by Transaction vs Master

```
Customs Workspace
│
├── Quick Access (Shortcuts)
│   ├── Sales Quote
│   ├── Declaration
│   ├── Permit Application          [NEW]
│   └── Exemption Certificate       [NEW]
│
├── Master Data
│   ├── Commodity
│   ├── Customs Authority
│   ├── Permit Type                 [NEW]
│   └── Exemption Type              [NEW]
│
└── Transactions
    ├── Declaration
    ├── Permit Application          [NEW]
    └── Exemption Certificate       [NEW]
```

---

## Step-by-Step: Adding to Workspace via Frappe UI

### Method 1: Using Workspace Editor

1. Go to **Workspace** list
2. Open **Customs** workspace
3. Click **Edit** or **Customize**

#### To Add Shortcuts:
1. In the **Shortcuts** section, click **+ Add**
2. Fill in:
   - **Label**: "Permit Application"
   - **Link To**: Select "Permit Application" from dropdown
   - **Type**: DocType
   - **Doc View**: List
   - **Color**: Choose a color
3. Click **Save**

#### To Add Links (Cards):
1. In the **Links** section, click **+ Add**
2. For Card Break:
   - **Type**: Card Break
   - **Label**: "Permit Management"
3. Then add links:
   - **Type**: Link
   - **Label**: "Permit Type"
   - **Link To**: "Permit Type"
   - **Link Type**: DocType

### Method 2: Using Workspace Builder (Visual Editor)

1. Go to **Workspace** → **Customs**
2. Click **Customize** (if available)
3. Use drag-and-drop to add:
   - New shortcuts
   - New cards
   - New links

---

## Complete List of New DocTypes

### Master Data (Add to "Master Files" or new "Master Data" card):
1. ✅ **Permit Type** - `Permit Type`
2. ✅ **Exemption Type** - `Exemption Type`

### Transactions (Add as Shortcuts or Links):
1. ✅ **Permit Application** - `Permit Application`
2. ✅ **Exemption Certificate** - `Exemption Certificate`

### Child Tables (No need to add - accessed via parent):
- Permit Requirement (accessed via Declaration)
- Declaration Exemption (accessed via Declaration)
- Permit Type Commodity (accessed via Permit Type)
- Permit Type Country (accessed via Permit Type)
- Permit Application Attachment (accessed via Permit Application)
- Exemption Certificate Declaration (accessed via Exemption Certificate)
- Exemption Certificate Attachment (accessed via Exemption Certificate)

---

## Enhanced Declaration

The **Declaration** DocType already exists in the workspace. After migration, it will automatically have:
- **Permits** tab (with Permit Requirement child table)
- **Exemptions** tab (with Declaration Exemption child table)

No additional workspace entry needed - just use the existing Declaration link.

---

## Recommended Workspace JSON Structure

If you prefer to edit the JSON directly, here's the structure:

```json
{
  "shortcuts": [
    // Existing shortcuts
    { "label": "Sales Quote", "link_to": "Sales Quote", ... },
    { "label": "Declaration", "link_to": "Declaration", ... },
    // NEW shortcuts
    { "label": "Permit Application", "link_to": "Permit Application", "type": "DocType", "doc_view": "List", "color": "Blue" },
    { "label": "Exemption Certificate", "link_to": "Exemption Certificate", "type": "DocType", "doc_view": "List", "color": "Green" }
  ],
  "links": [
    // Existing Master Files card
    { "type": "Card Break", "label": "Master Files" },
    { "label": "Commodity", "link_to": "Commodity", ... },
    { "label": "Customs Authority", "link_to": "Customs Authority", ... },
    // NEW master data
    { "label": "Permit Type", "link_to": "Permit Type", "type": "DocType" },
    { "label": "Exemption Type", "link_to": "Exemption Type", "type": "DocType" },
    // NEW Permit Management card
    { "type": "Card Break", "label": "Permit Management" },
    { "label": "Permit Type", "link_to": "Permit Type", "type": "DocType" },
    { "label": "Permit Application", "link_to": "Permit Application", "type": "DocType" },
    // NEW Exemption Management card
    { "type": "Card Break", "label": "Exemption Management" },
    { "label": "Exemption Type", "link_to": "Exemption Type", "type": "DocType" },
    { "label": "Exemption Certificate", "link_to": "Exemption Certificate", "type": "DocType" }
  ]
}
```

---

## Quick Reference: DocType Names

Use these exact names when adding to workspace:

| Display Name | DocType Name |
|-------------|-------------|
| Permit Type | `Permit Type` |
| Permit Application | `Permit Application` |
| Exemption Type | `Exemption Type` |
| Exemption Certificate | `Exemption Certificate` |
| Declaration | `Declaration` (already exists) |

---

## Notes

- **Child tables** don't need workspace entries - they're accessed via their parent DocTypes
- **Declaration** already exists - it will automatically show the new Permits and Exemptions tabs after migration
- Add **Permit Application** and **Exemption Certificate** as shortcuts for quick access
- Add **Permit Type** and **Exemption Type** to Master Files section
- Consider creating separate cards for better organization

---

**After Migration**: Run `bench migrate` first, then add these to the workspace via the Frappe UI.

