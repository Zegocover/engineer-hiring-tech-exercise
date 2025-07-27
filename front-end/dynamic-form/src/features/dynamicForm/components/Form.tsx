import { Stack } from "@chakra-ui/react";
import { yupResolver } from "@hookform/resolvers/yup";
import { useForm } from "react-hook-form";
import { FormConfig, FormValues } from "../types";
import { buildSchemaFromConfig, buildValuesFromConfig } from "../utils";
import { FormField } from "./FormField";

interface FormProps {
  formData: FormConfig;
  onSubmit: (data: FormValues) => void;
  isLoading: boolean;
}

export const Form = ({ formData, onSubmit, isLoading }: FormProps) => {
  const defaultValues = buildValuesFromConfig(formData);
  const schema = buildSchemaFromConfig(formData);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isLoading: formLoading },
  } = useForm({ defaultValues, resolver: yupResolver(schema) });
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Stack gap="4" align="flex-start" maxW="sm">
        {formData.map((field) => (
          <FormField
            control={control}
            key={field.id}
            fieldData={field}
            isLoading={isLoading || formLoading}
            register={register}
            errors={errors}
          />
        ))}
      </Stack>
    </form>
  );
};
