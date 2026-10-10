-- Relational model for the Procure-to-Receive mock dataset (SQLite).
-- Source of truth: data/mock_data_schema.json. Names are kept as in the source
-- so the semantic layer maps 1:1. Only source facts are stored here; derived
-- values (projected stock, shortfall, spare stock) are computed in code.

-- SQLite enforces foreign keys per connection, not per database file.
-- Always open the database via load_sqlite.connect(), which turns them on.
PRAGMA foreign_keys = ON;

CREATE TABLE Vendor (
    vendorId            TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    country             TEXT NOT NULL,
    avgLeadTimeDays     INTEGER NOT NULL CHECK (avgLeadTimeDays >= 0),
    onTimeDeliveryRate  REAL NOT NULL CHECK (onTimeDeliveryRate BETWEEN 0 AND 1),
    qualityRating       TEXT NOT NULL CHECK (qualityRating IN ('A', 'B', 'C'))
);

-- Grain: one material at one plant (the inventory grain).
-- materialId / plantId are kept as attributes; splitting out Material and
-- Plant tables is a deferred, additive change (see erd.md).
CREATE TABLE MaterialPlant (
    materialPlantId      TEXT PRIMARY KEY,
    materialId           TEXT NOT NULL,
    materialDescription  TEXT NOT NULL,
    plantId              TEXT NOT NULL,
    plantName            TEXT NOT NULL,
    baseUnit             TEXT NOT NULL,
    onHandQuantity       REAL NOT NULL CHECK (onHandQuantity >= 0),
    safetyStock          REAL NOT NULL CHECK (safetyStock >= 0),
    reorderPoint         REAL NOT NULL CHECK (reorderPoint >= 0),
    standardCost         REAL NOT NULL CHECK (standardCost >= 0),
    UNIQUE (materialId, plantId)
);

-- Junction table for Vendor.approvedForMaterials (many-to-many).
CREATE TABLE VendorApproval (
    vendorId         TEXT NOT NULL REFERENCES Vendor (vendorId),
    materialPlantId  TEXT NOT NULL REFERENCES MaterialPlant (materialPlantId),
    PRIMARY KEY (vendorId, materialPlantId)
);

-- Demand against a material-plant. Joins to supply only via MaterialPlant.
CREATE TABLE MaterialRequirements (
    requirementId        TEXT PRIMARY KEY,
    materialPlantId      TEXT NOT NULL REFERENCES MaterialPlant (materialPlantId),
    requirementType      TEXT NOT NULL CHECK (requirementType IN ('ProductionOrder', 'SalesOrder', 'Forecast')),
    requirementQuantity  REAL NOT NULL CHECK (requirementQuantity >= 0),
    requirementDate      TEXT NOT NULL,
    priority             TEXT NOT NULL CHECK (priority IN ('High', 'Medium', 'Low')),
    status               TEXT NOT NULL CHECK (status IN ('Open', 'PartiallyCovered', 'Covered'))
);

-- Requisition: a request to procure a material-plant.
CREATE TABLE PurchaseRequirement (
    purchaseRequirementId  TEXT PRIMARY KEY,
    materialPlantId        TEXT NOT NULL REFERENCES MaterialPlant (materialPlantId),
    requestedQuantity      REAL NOT NULL CHECK (requestedQuantity >= 0),
    neededByDate           TEXT NOT NULL,
    createdDate            TEXT NOT NULL,
    status                 TEXT NOT NULL CHECK (status IN ('Open', 'Converted', 'Closed'))
);

-- Purchase order header.
CREATE TABLE PurchaseDocument (
    purchaseDocumentId  TEXT PRIMARY KEY,
    documentType        TEXT NOT NULL CHECK (documentType IN ('PurchaseOrder')),
    vendorId            TEXT NOT NULL REFERENCES Vendor (vendorId),
    documentDate        TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('Open', 'PartiallyReceived', 'Closed')),
    currency            TEXT NOT NULL
);

-- Purchase order line: the inbound supply, with its confirmed delivery date.
CREATE TABLE PurchaseDocumentLine (
    purchaseDocumentLineId  TEXT PRIMARY KEY,
    purchaseDocumentId      TEXT NOT NULL REFERENCES PurchaseDocument (purchaseDocumentId),
    lineNumber              INTEGER NOT NULL CHECK (lineNumber > 0),
    materialPlantId         TEXT NOT NULL REFERENCES MaterialPlant (materialPlantId),
    purchaseRequirementId   TEXT NOT NULL REFERENCES PurchaseRequirement (purchaseRequirementId),
    orderedQuantity         REAL NOT NULL CHECK (orderedQuantity >= 0),
    netPrice                REAL NOT NULL CHECK (netPrice >= 0),
    requestedDeliveryDate   TEXT NOT NULL,
    confirmedDeliveryDate   TEXT NOT NULL,
    goodsReceiptQuantity    REAL NOT NULL CHECK (goodsReceiptQuantity >= 0),
    lineStatus              TEXT NOT NULL CHECK (lineStatus IN ('Open', 'Confirmed', 'Delayed', 'PartiallyReceived', 'Received')),
    UNIQUE (purchaseDocumentId, lineNumber)
);

-- Append-only event log. Generic reference (objectType + objectId): objectId
-- points to a different table per objectType, so it cannot be a database FK.
-- load_sqlite.py validates every reference instead.
CREATE TABLE Event (
    eventId     TEXT PRIMARY KEY,
    objectType  TEXT NOT NULL CHECK (objectType IN (
                    'Vendor', 'MaterialPlant', 'MaterialRequirements',
                    'PurchaseRequirement', 'PurchaseDocument', 'PurchaseDocumentLine')),
    objectId    TEXT NOT NULL,
    activity    TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    attributes  TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(attributes))
);

CREATE INDEX idx_event_object ON Event (objectType, objectId);
