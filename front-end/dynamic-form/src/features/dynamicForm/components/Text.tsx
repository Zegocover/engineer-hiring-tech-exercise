import { forwardRef } from "react";
import { Text as ChakraText } from "@chakra-ui/react";
import { TextField } from "../types";

export type InputProps = TextField;

const Text = forwardRef<HTMLInputElement, InputProps>(({ value }, ref) => {
  return <ChakraText ref={ref}>{value}</ChakraText>;
});
Text.displayName = "Text";

export { Text };
