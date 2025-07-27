import {
  FieldErrors,
  UseFormRegister,
  Control,
  FieldValues,
} from "react-hook-form";

import { Text } from "./Text";
import { FieldType, FormField as FormFieldType, FormValues } from "../types";
import { Input } from "./Input";
import { Button } from "./Button";
import { Select } from "./Select";

interface FormFieldProps {
  fieldData: FormFieldType;
  isLoading: boolean;
  register: UseFormRegister<FormValues>;
  control: Control<FieldValues>;
  errors: FieldErrors;
}

export const FormField = ({
  fieldData,
  isLoading,
  register,
  control,
  errors,
}: FormFieldProps) => {
  switch (fieldData.type) {
    case FieldType.Text:
      return <Text {...fieldData} />;

    case FieldType.Input:
      return <Input {...fieldData} register={register} errors={errors} />;

    case FieldType.Dropdown:
      return (
        <Select
          field={fieldData}
          control={control}
          errors={errors}
          disabled={!!fieldData.disabled}
        />
      );

    case FieldType.Button:
      return (
        <Button
          {...fieldData}
          type="submit"
          disabled={!!fieldData.disabled}
          loading={isLoading}
        >
          {fieldData.value}
        </Button>
      );

    default:
      return null;
  }
};
