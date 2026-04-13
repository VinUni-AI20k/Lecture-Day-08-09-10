with import <nixpkgs> { };
pkgs.mkShell {
  name = "lab8";

  # Use LD_LIBRARY_PATH so pre-compiled pip/uv wheels can find the C-libraries
  LD_LIBRARY_PATH = lib.makeLibraryPath [
    stdenv.cc.cc.lib
    zlib
  ];

  SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";

  packages = with pkgs; [
    uv
  ];
}
