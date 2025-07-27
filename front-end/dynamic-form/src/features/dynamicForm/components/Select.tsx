import {
  Select as ChakraSelect,
  Portal,
  createListCollection,
  Field,
} from "@chakra-ui/react";
import { Controller, Control, FieldErrors, FieldValues } from "react-hook-form";
import { DropdownField } from "../types";

interface SelectProps {
  field: DropdownField;
  control: Control<FieldValues>;
  errors?: FieldErrors;
  disabled?: boolean;
}

export const Select = ({
  field,
  control,
  errors,
  disabled = false,
}: SelectProps) => {
  const { name, label, options, placeholder = "Select option", value } = field;
  const collection = createListCollection({ items: options });

  const error = errors?.[name];
  const errorMessage = Array.isArray(error)
    ? error[0]?.message
    : error?.message;

  return (
    <Field.Root invalid={!!error}>
      <Field.Label>{label}</Field.Label>

      <Controller
        name={name}
        control={control}
        defaultValue={value ?? placeholder}
        render={({ field: { onChange, value } }) => (
          <ChakraSelect.Root
            collection={collection}
            value={value}
            onValueChange={({ value }) => onChange(value)}
            disabled={disabled}
          >
            <ChakraSelect.HiddenSelect />
            <ChakraSelect.Control>
              <ChakraSelect.Trigger>
                <ChakraSelect.ValueText placeholder={placeholder} />
              </ChakraSelect.Trigger>
              <ChakraSelect.IndicatorGroup>
                <ChakraSelect.Indicator />
              </ChakraSelect.IndicatorGroup>
            </ChakraSelect.Control>

            <Portal>
              <ChakraSelect.Positioner>
                <ChakraSelect.Content>
                  {options.map((opt) => (
                    <ChakraSelect.Item key={opt.value} item={opt}>
                      {opt.label}
                      <ChakraSelect.ItemIndicator />
                    </ChakraSelect.Item>
                  ))}
                </ChakraSelect.Content>
              </ChakraSelect.Positioner>
            </Portal>
          </ChakraSelect.Root>
        )}
      />

      <Field.ErrorText>{errorMessage}</Field.ErrorText>
    </Field.Root>
  );
};
