//! SHACL validator implementation of `ValidatorPort`.
//!
//! Current implementation provides a profile-based execution path for
//! `dp-record-metadata` constraints and returns structured violations.
//! This keeps SHACL validation operational while a full graph-native SHACL
//! engine integration is finalized.

use async_trait::async_trait;
use hex_core::domain::{
    error::ValidatorError,
    model::ArtifactSet,
    validation::{Severity, ValidationResult, ValidationViolation, ValidatorKind},
};
use hex_core::ports::outbound::validator::ValidatorPort;
use time::{format_description::well_known::Rfc3339, OffsetDateTime};

pub struct ShaclValidator;

impl ShaclValidator {
    pub fn new() -> Self {
        Self
    }
}

impl Default for ShaclValidator {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ValidatorPort for ShaclValidator {
    fn kind(&self) -> ValidatorKind {
        ValidatorKind::Shacl
    }

    async fn validate(
        &self,
        artifacts: &ArtifactSet,
        payload: &serde_json::Value,
    ) -> Result<ValidationResult, ValidatorError> {
        let shacl = match &artifacts.shacl {
            Some(s) => s,
            None => {
                // No SHACL artifact present — skip gracefully.
                return Ok(ValidationResult {
                    kind: ValidatorKind::Shacl,
                    passed: true,
                    violations: vec![],
                });
            }
        };

        let _ = shacl;
        let mut violations = Vec::new();

        validate_record_scope(payload, &mut violations);
        validate_related_passports(payload, &mut violations);
        validate_metadata_versioning(payload, &mut violations);
        validate_applied_schemas(payload, &mut violations);

        Ok(ValidationResult {
            kind: ValidatorKind::Shacl,
            passed: violations.is_empty(),
            violations,
        })
    }
}

fn validate_record_scope(payload: &serde_json::Value, violations: &mut Vec<ValidationViolation>) {
    if let Some(scope) = payload.get("record_scope") {
        let valid = matches!(scope.as_str(), Some("product" | "material"));
        if !valid {
            push_violation(
                violations,
                "$.record_scope",
                "record_scope must be one of: product, material",
            );
        }
    }
}

fn validate_related_passports(
    payload: &serde_json::Value,
    violations: &mut Vec<ValidationViolation>,
) {
    const ALLOWED: &[&str] = &[
        "derived_from",
        "contributes_to",
        "split_from",
        "merged_into",
        "recycled_into",
        "manufactured_from",
    ];

    if let Some(items) = payload.get("related_passports").and_then(|v| v.as_array()) {
        for (idx, item) in items.iter().enumerate() {
            if let Some(relation_type) = item.get("relation_type") {
                let ok = relation_type
                    .as_str()
                    .map(|v| ALLOWED.contains(&v))
                    .unwrap_or(false);
                if !ok {
                    push_violation(
                        violations,
                        format!("$.related_passports[{idx}].relation_type"),
                        "relation_type is not allowed by SHACL shape",
                    );
                }
            }
        }
    }
}

fn validate_metadata_versioning(
    payload: &serde_json::Value,
    violations: &mut Vec<ValidationViolation>,
) {
    let Some(meta) = payload
        .get("metadata_versioning")
        .and_then(|v| v.as_object())
    else {
        return;
    };

    for key in ["metadata_created", "metadata_modified"] {
        if let Some(value) = meta.get(key) {
            let Some(text) = value.as_str() else {
                push_violation(
                    violations,
                    format!("$.metadata_versioning.{key}"),
                    "value must be an RFC3339 date-time string",
                );
                continue;
            };
            if OffsetDateTime::parse(text, &Rfc3339).is_err() {
                push_violation(
                    violations,
                    format!("$.metadata_versioning.{key}"),
                    "value is not a valid RFC3339 date-time",
                );
            }
        }
    }
}

fn validate_applied_schemas(
    payload: &serde_json::Value,
    violations: &mut Vec<ValidationViolation>,
) {
    let Some(items) = payload.get("applied_schemas").and_then(|v| v.as_array()) else {
        return;
    };
    const ALLOWED_KEYS: &[&str] = &["schema_reference", "schema_usage", "composition_info"];

    for (idx, item) in items.iter().enumerate() {
        if let Some(obj) = item.as_object() {
            for key in obj.keys() {
                if !ALLOWED_KEYS.contains(&key.as_str()) {
                    push_violation(
                        violations,
                        format!("$.applied_schemas[{idx}].{key}"),
                        "property is not allowed by closed SHACL shape",
                    );
                }
            }
        }

        if let Some(seq) = item
            .get("composition_info")
            .and_then(|v| v.get("sequence_order"))
            .filter(|v| !v.is_null())
        {
            if seq.as_i64().is_none() {
                push_violation(
                    violations,
                    format!("$.applied_schemas[{idx}].composition_info.sequence_order"),
                    "sequence_order must be an integer",
                );
            }
        }

        if let Some(pct) = item
            .get("schema_usage")
            .and_then(|v| v.get("completeness_percentage"))
            .filter(|v| !v.is_null())
        {
            if pct.as_f64().is_none() {
                push_violation(
                    violations,
                    format!("$.applied_schemas[{idx}].schema_usage.completeness_percentage"),
                    "completeness_percentage must be a number",
                );
            }
        }
    }
}

fn push_violation(
    violations: &mut Vec<ValidationViolation>,
    path: impl Into<String>,
    message: impl Into<String>,
) {
    violations.push(ValidationViolation {
        path: Some(path.into()),
        message: message.into(),
        severity: Severity::Error,
    });
}
