#!/data/data/com.termux/files/usr/bin/bash
# Redmi Note 7 — Unidirectional Control Node Setup
set -e

echo "[*] Setting up OpenSSH and isolated authorized keys..."
pkg update -y 2>/dev/null || true
pkg install -y openssh 2>/dev/null || true

mkdir -p ~/.ssh
cat << 'KEY_EOF' > ~/.ssh/authorized_keys
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOinAKKduA+9ZZz+wVbxGIdkkJFWNQNrereuOZDa31l+ japan@vps-arm-ubuntu
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDsYVsfWjzRWhD/fzN9fzN2W7WTinzNWeGdxmt3lAG5i fitness@vps-arm-ubuntu
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHUqnRniejWO0AZMiNIk3Kj+Oh5wr2/tzJfk8prbssnr smashbot@ubuntu
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBqlglor8teLd3ig2FxMCp/eR8WgwROQSlKiq4lAfsdA calq
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICuL5YS4mlkx9hnMIfKDx1fWBbJoE5qLuRzYys3aHgTe ssbu_brain
KEY_EOF

cat << 'TUNNEL_KEY_EOF' > ~/.ssh/id_tunnel
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAJwlJ7NFbghsa4SZLPv7mZu/2dI012Er3x38QLIbV4QgAAAKCHSRRah0kU
WgAAAAtzc2gtZWQyNTUxOQAAACAJwlJ7NFbghsa4SZLPv7mZu/2dI012Er3x38QLIbV4Qg
AAAEBwpTFsXk8L01CXBSeypiqpRk7HzYsY8Uwrbb0Glo7ItgnCUns0VuCGxrhJks+/uZm7
/Z0jTXYSvfHfxAshtXhCAAAAG3JlZG1pLXVuaWRpcmVjdGlvbmFsLXR1bm5lbAEC
-----END OPENSSH PRIVATE KEY-----
TUNNEL_KEY_EOF

chmod 700 ~
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys ~/.ssh/id_tunnel
mkdir -p "$PREFIX/etc/ssh"
cp ~/.ssh/authorized_keys "$PREFIX/etc/ssh/authorized_keys" 2>/dev/null || true
chmod 600 "$PREFIX/etc/ssh/authorized_keys" 2>/dev/null || true

# Configure sshd for passwordless key auth
mkdir -p "$PREFIX/etc/ssh"
touch "$PREFIX/etc/ssh/sshd_config"
grep -q "StrictModes no" "$PREFIX/etc/ssh/sshd_config" || echo "StrictModes no" >> "$PREFIX/etc/ssh/sshd_config"
grep -q "PubkeyAuthentication yes" "$PREFIX/etc/ssh/sshd_config" || echo "PubkeyAuthentication yes" >> "$PREFIX/etc/ssh/sshd_config"
grep -q "AuthorizedKeysFile" "$PREFIX/etc/ssh/sshd_config" || echo "AuthorizedKeysFile .ssh/authorized_keys etc/ssh/authorized_keys" >> "$PREFIX/etc/ssh/sshd_config"

termux-wake-lock 2>/dev/null || true
pkill sshd 2>/dev/null || true
sshd

pkill -f 'id_tunnel' 2>/dev/null || true
(
  while true; do
    ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes -i ~/.ssh/id_tunnel -N -R 2222:localhost:8022 japan@japan.calq.it 2>/dev/null || true
    sleep 3
  done
) >/dev/null 2>&1 &

USER_NAME=$(whoami)

echo ""
echo "============================================================"
echo "🎌 REDMI NOTE 7 — COLLEGAMENTO UNIDIREZIONALE ATTIVO"
echo "============================================================"
echo "• Utente Termux : $USER_NAME"
echo "• Porta Ingress : 2222 (Tunnel crittografico isolato)"
echo "============================================================"
echo "[✓] Tunnel inverso attivo. L'agent può interagire col telefono."

