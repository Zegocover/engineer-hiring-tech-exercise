import * as yup from "yup";
import { FormConfig, FieldType, FormValues } from "../types";

export function buildValuesFromConfig(config: FormConfig) {
  const filtered = config.filter(
    (field) => field.type !== FieldType.Button && field.type !== FieldType.Text
  );

  return filtered.reduce((acc, field) => {
    if (field.name && field.value !== undefined) {
      acc[field.name] = field.value;
    }
    return acc;
  }, {} as FormValues);
}

export function buildSchemaFromConfig(config: FormConfig): yup.AnyObjectSchema {
  const shape: Record<string, yup.AnySchema> = {};

  config.forEach((field) => {
    if (
      !field.name ||
      field.type === FieldType.Text ||
      field.type === FieldType.Button
    )
      return;

    let schema: yup.AnySchema = yup.string();

    if (field.type === FieldType.Dropdown) {
      const allowed = field.options?.map((o) => o.value) ?? [];
      schema = yup
        .array()
        .of(yup.string().oneOf(allowed, "Invalid option"))
        .min(1, "Please select an option");
    }

    if (field.validation?.required) {
      schema = schema.required("This field is required");
    }
    if (field.validation?.pattern) {
      schema = (schema as yup.StringSchema).matches(
        new RegExp(field.validation.pattern),
        "Invalid format"
      );
    }

    shape[field.name] = schema;
  });

  return yup.object().shape(shape);
}
