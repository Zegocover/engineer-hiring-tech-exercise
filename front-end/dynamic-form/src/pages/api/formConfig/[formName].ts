import type { NextApiRequest, NextApiResponse } from "next";
import personalDetails from "@/features/dynamicForm/configs/personalDetails.json";
import { FormValues } from "@/features/dynamicForm";

type Data = {
  formName: string;
  data: unknown;
};

type PostResponse = {
  success: boolean;
  message: string;
  receivedData?: FormValues;
};

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data | PostResponse>
) {
  const { formName } = req.query as { formName: string };

  if (req.method === "GET") {
    if (formName === "personalDetails") {
      return res.status(200).json({ formName, data: personalDetails });
    }

    return res.status(404).json({
      formName,
      data: { message: "Form config not found" },
    });
  }

  if (req.method === "POST") {
    const submittedData = req.body;

    return res.status(200).json({
      success: true,
      message: `Form "${formName}" submitted successfully`,
      receivedData: submittedData,
    });
  }

  return res
    .setHeader("Allow", ["GET", "POST"])
    .status(405)
    .end("Method Not Allowed");
}
