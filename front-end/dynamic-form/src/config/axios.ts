import axios, { AxiosInstance } from "axios";

let axiosClient: AxiosInstance | null = null;

export const createAxiosServerClient = () => {
  const protocol = process.env.NODE_ENV === "development" ? "http" : "https";
  const host =
    process.env.NODE_ENV === "development"
      ? "localhost:3000"
      : "server.somewhere";

  axiosClient = axios.create({
    baseURL: `${protocol}://${host}`,
    headers: {},
  });

  return axiosClient;
};

export const http = axiosClient ?? createAxiosServerClient();
