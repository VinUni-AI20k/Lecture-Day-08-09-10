{
  description = "Python development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pip
            python3Packages.virtualenv
            stdenv.cc.cc.lib
            # Add other system dependencies here (e.g., git, sqlite)
          ];

          shellHook = ''
            # Make C/C++ runtime libs visible for binary wheels (numpy, chromadb deps).
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}:$LD_LIBRARY_PATH"
            echo "Python development shell loaded!"
            if [ ! -d .venv ]; then
              python -m venv .venv
            fi
            source .venv/bin/activate
            pip install uv
            uv pip install -r requirements.txt
          '';
        };
      });
}