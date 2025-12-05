-- DuckDB schema for Keymark heat pump dataset
-- Hierarchy: Manufacturer -> Subtype (product line) -> Model (specific configuration)

CREATE OR REPLACE TABLE manufacturers (
    name TEXT PRIMARY KEY
);

CREATE OR REPLACE TABLE subtypes (
    manufacturer_name TEXT NOT NULL,
    subtype_name TEXT NOT NULL,
    metadata JSON,
    PRIMARY KEY (manufacturer_name, subtype_name)
);

CREATE OR REPLACE TABLE models (
    manufacturer_name TEXT NOT NULL,
    subtype_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    properties JSON,
    PRIMARY KEY (manufacturer_name, subtype_name, model_name)
);

CREATE OR REPLACE TABLE measurements (
    manufacturer_name TEXT NOT NULL,
    subtype_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    en_code TEXT NOT NULL,
    dimension TEXT NOT NULL,
    value DOUBLE,
    unit TEXT
);

CREATE INDEX IF NOT EXISTS idx_measurements_en ON measurements(en_code);
CREATE INDEX IF NOT EXISTS idx_measurements_dim ON measurements(dimension);
CREATE INDEX IF NOT EXISTS idx_measurements_model ON measurements(manufacturer_name, subtype_name, model_name);
