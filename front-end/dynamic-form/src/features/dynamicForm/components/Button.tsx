import {
  AbsoluteCenter,
  Button as ChakraButton,
  ButtonProps as ChakraButtonProps,
  Spinner,
} from "@chakra-ui/react";
import * as React from "react";

export interface ButtonProps extends ChakraButtonProps {
  loading?: boolean;
  loadingText?: string;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ loading, disabled, loadingText, children, ...rest }, ref) => {
    return (
      <ChakraButton ref={ref} disabled={loading || disabled} {...rest}>
        {loading && !loadingText ? (
          <>
            <AbsoluteCenter display="inline-flex">
              <Spinner size="inherit" color="inherit" />
            </AbsoluteCenter>
            <span style={{ opacity: 0 }}>{children}</span>
          </>
        ) : loading && loadingText ? (
          <>
            <Spinner size="inherit" color="inherit" mr={2} />
            {loadingText}
          </>
        ) : (
          children
        )}
      </ChakraButton>
    );
  }
);

Button.displayName = "Button";
