import { http } from "@/config";
import { useQuery } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { FormConfig, FormValues } from "../types";

interface GetFormDataResponse {
  formName: string;
  data: FormConfig;
}

export const useGetFormData = (
  formName: string,
  initialData: GetFormDataResponse
) => {
  return useQuery<GetFormDataResponse>({
    queryKey: ["formData"],
    queryFn: () => getFormData(formName),
    initialData,
  });
};

export const getFormData = async (formName: string) => {
  const formData = await http<GetFormDataResponse>(
    `/api/formConfig/${formName}`
  );
  return formData.data;
};

export const submitFormData = async (formName: string, payload: FormValues) => {
  const response = await http.post(`/api/formConfig/${formName}`, payload);
  return response.data;
};

export const useSubmitFormData = (formName: string, onSuccess: () => void) => {
  return useMutation({
    mutationFn: (payload: FormValues) => submitFormData(formName, payload),
    onSuccess,
  });
};
