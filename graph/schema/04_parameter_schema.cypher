// -----------------------------------------------------------------------------
// 04_parameter_schema.cypher
//
// Purpose:
// Add parameter-level schema metadata for the MVP datasheet.
//
// This file enriches ParameterType nodes with:
// - aliases;
// - screening keywords;
// - extraction hints;
// - whether a unit is expected;
// - whether the parameter is string/categorical or physical;
// - MVP priority.
//
// These metadata fields are used by:
// - document screening;
// - graph-guided prompt construction;
// - vocabulary grounding;
// - validation.
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// Manufacturer
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "Manufacturer"})
SET
  pt.display_name = "Manufacturer",
  pt.parameter_category = "identification",
  pt.expects_unit = false,
  pt.screening_weight = 1,
  pt.extraction_hint = "Extract the company or manufacturer name of the device.",
  pt.aliases = [
    "manufacturer",
    "company",
    "vendor",
    "supplier",
    "Vishay",
    "Vishay Semiconductors"
  ],
  pt.screening_keywords = [
    "manufacturer",
    "Vishay",
    "Vishay Semiconductors"
  ];

// -----------------------------------------------------------------------------
// ProductModel
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "ProductModel"})
SET
  pt.display_name = "Product model",
  pt.parameter_category = "identification",
  pt.expects_unit = false,
  pt.screening_weight = 4,
  pt.extraction_hint = "Extract the exact product model or part number described by the datasheet.",
  pt.aliases = [
    "product model",
    "model",
    "part number",
    "part no.",
    "device",
    "type",
    "TEMT6000X01"
  ],
  pt.screening_keywords = [
    "TEMT6000X01",
    "ambient light sensor",
    "datasheet"
  ];

// -----------------------------------------------------------------------------
// DeviceType
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "DeviceType"})
SET
  pt.display_name = "Device type",
  pt.parameter_category = "identification",
  pt.expects_unit = false,
  pt.screening_weight = 3,
  pt.extraction_hint = "Extract the general type of device described by the datasheet.",
  pt.aliases = [
    "device type",
    "product type",
    "sensor type",
    "ambient light sensor",
    "light sensor",
    "photo sensor",
    "photosensor"
  ],
  pt.screening_keywords = [
    "ambient light sensor",
    "light sensor",
    "photosensor"
  ];

// -----------------------------------------------------------------------------
// PackageType
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "PackageType"})
SET
  pt.display_name = "Package type",
  pt.parameter_category = "packaging",
  pt.expects_unit = false,
  pt.screening_weight = 2,
  pt.extraction_hint = "Extract the general package or mounting type, such as surface-mount package.",
  pt.aliases = [
    "package type",
    "mounting type",
    "surface mount",
    "surface-mount",
    "SMD",
    "SMT"
  ],
  pt.screening_keywords = [
    "package",
    "surface mount",
    "surface-mount",
    "SMD"
  ];

// -----------------------------------------------------------------------------
// PackageForm
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "PackageForm"})
SET
  pt.display_name = "Package form",
  pt.parameter_category = "packaging",
  pt.expects_unit = false,
  pt.screening_weight = 3,
  pt.extraction_hint = "Extract the specific package form or package code, such as 1206.",
  pt.aliases = [
    "package form",
    "package code",
    "package size",
    "case size",
    "1206"
  ],
  pt.screening_keywords = [
    "1206",
    "package",
    "package size",
    "case size"
  ];

// -----------------------------------------------------------------------------
// Dimensions
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "Dimensions"})
SET
  pt.display_name = "Dimensions",
  pt.parameter_category = "physical_dimension",
  pt.expects_unit = true,
  pt.screening_weight = 4,
  pt.extraction_hint = "Extract the physical dimensions of the device. Preserve the dimensional expression and unit, for example 4 x 2 x 1.05 mm.",
  pt.aliases = [
    "dimensions",
    "dimension",
    "size",
    "length",
    "width",
    "height",
    "L x W x H"
  ],
  pt.screening_keywords = [
    "dimensions",
    "dimension",
    "size",
    "length",
    "width",
    "height",
    "mm"
  ];

// -----------------------------------------------------------------------------
// PeakSensitivityWavelength
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "PeakSensitivityWavelength"})
SET
  pt.display_name = "Peak sensitivity wavelength",
  pt.parameter_category = "optical",
  pt.expects_unit = true,
  pt.screening_weight = 5,
  pt.extraction_hint = "Extract the wavelength at which the sensor has peak sensitivity. The value is typically expressed in nm.",
  pt.aliases = [
    "peak sensitivity",
    "peak wavelength",
    "wavelength of peak sensitivity",
    "spectral sensitivity",
    "lambda p",
    "λp",
    "sensitivity wavelength"
  ],
  pt.screening_keywords = [
    "peak sensitivity",
    "peak wavelength",
    "spectral sensitivity",
    "wavelength",
    "λp",
    "nm"
  ];

// -----------------------------------------------------------------------------
// AngleOfHalfSensitivity
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "AngleOfHalfSensitivity"})
SET
  pt.display_name = "Angle of half sensitivity",
  pt.parameter_category = "optical",
  pt.expects_unit = true,
  pt.screening_weight = 3,
  pt.extraction_hint = "Extract the angle of half sensitivity. The value may be expressed as an angular range such as ±60 degree.",
  pt.aliases = [
    "angle of half sensitivity",
    "half sensitivity angle",
    "viewing angle",
    "angle",
    "±60",
    "+/-60"
  ],
  pt.screening_keywords = [
    "angle of half sensitivity",
    "half sensitivity",
    "viewing angle",
    "angle",
    "degree"
  ];