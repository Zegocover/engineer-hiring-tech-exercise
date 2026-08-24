{
  description = "Zego single-domain asynchronous web crawler";
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShellNoCC {
          name = "zego-crawler";
          meta.description = "Development shell for the Zego web crawler";
          packages = [
            pkgs.python313
            pkgs.uv
            pkgs.ruff
            pkgs.gnumake
          ];

          env = {
            UV_PYTHON = "${pkgs.python313}/bin/python3.13"; # Resolve against the Nix interpreter.
            UV_PYTHON_DOWNLOADS = "never";                  # Never fetch a foreign interpreter.
            RUFF = "${pkgs.ruff}/bin/ruff";                 # Use the Nix ruff; the wheel won't run on NixOS.
          };
        };
      });
    };
}
