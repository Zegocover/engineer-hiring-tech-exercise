export enum FieldType {
  Text = "text",
  Input = "input",
  Dropdown = "dropdown",
  Button = "button",
}

export interface ConditionalRule {
  dependsOn: string;
  value: string;
}

export interface ValidationRule {
  required?: boolean;
  pattern?: string;
  dependsOn?: {
    field: string;
    condition: "notEmpty" | "equals" | "notEquals";
  };
}

export interface BaseField {
  id: string;
  name: string;
  type: FieldType;
  disabled?: boolean;
  validation?: ValidationRule | null;
}

export interface TextField extends BaseField {
  type: FieldType.Text;
  placeholder: string;
  value: string;
}

export interface ButtonField extends BaseField {
  type: FieldType.Button;
  value: string;
}

export interface InputField extends BaseField {
  type: FieldType.Input;
  placeholder?: string;
  label: string;
  value?: string;
}

export interface DropdownField extends BaseField {
  type: FieldType.Dropdown;
  label: string;
  placeholder?: string;
  options: { label: string; value: string }[];
  value?: string;
}

export type FormField = TextField | InputField | ButtonField | DropdownField;

export type FormConfig = FormField[];

export type FormValues = Record<string, string | boolean | null | undefined>;
