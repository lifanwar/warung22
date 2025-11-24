{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [
    pkgs.python312
    pkgs.gcc.cc.lib  # Menyediakan libstdc++.so.6
    pkgs.zlib
    pkgs.openssl
  ];
  
  shellHook = ''
    # Set library path untuk GCC
    export LD_LIBRARY_PATH=${pkgs.gcc.cc.lib}/lib:$LD_LIBRARY_PATH
    
    # Jika virtual environment belum ada, buat dengan nama .venv
    if [ ! -d ".venv" ]; then
      python3 -m venv .venv
      echo "Virtual environment .venv berhasil dibuat."
    fi

    # Aktifkan virtual environment
    source .venv/bin/activate

    # Upgrade pip dan install paket kurigram
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Environment siap. Virtual environment sudah aktif dan paket perplexity telah diinstall."
  '';
}
