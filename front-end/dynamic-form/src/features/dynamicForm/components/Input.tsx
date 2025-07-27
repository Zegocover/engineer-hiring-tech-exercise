import { Input as ChakraInput, Field } from "@chakra-ui/react";
import {
  FieldError,
  FieldErrors,
  FieldValues,
  UseFormRegister,
} from "react-hook-form";

import { InputField } from "../types";

interface InputProps extends InputField {
  register: UseFormRegister<FieldValues>;
  errors?: FieldErrors;
}

export const Input = ({
  name,
  label,
  register,
  errors,
  type,
  disabled,
}: InputProps) => {
  const error = errors?.[name];
  const errorMessage: string | undefined = Array.isArray(error)
    ? error[0]?.message
    : (error as FieldError | undefined)?.message;
  return (
    <Field.Root invalid={!!error}>
      <Field.Label>{label}</Field.Label>
      <ChakraInput
        type={type}
        {...register(name)}
        name={name}
        disabled={disabled}
      />
      <Field.ErrorText>{errorMessage}</Field.ErrorText>
    </Field.Root>
  );
};
