import os
import qrcode
from PIL import Image

class QRCodeService:
    """Serviço para geração e gerenciamento de QR codes"""

    def __init__(self, base_dir="static/qrcodes"):
        self.base_dir = base_dir
        self._criar_pasta_se_nao_existir()

    def _criar_pasta_se_nao_existir(self):
        """Cria a pasta de QR codes se ela não existir"""
        os.makedirs(self.base_dir, exist_ok=True)

    def _salvar_qr(self, img, nome_arquivo):
        """Salva o QR code na pasta especificada"""
        caminho = os.path.join(self.base_dir, nome_arquivo)
        img.save(caminho)
        print(f"QR salvo em: {caminho}")
        return caminho

    def gerar_qr_padrao(self, data, nome_arquivo="qrcode_padrao.png"):
        """Gera um QR code padrão (preto e branco)"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        caminho = self._salvar_qr(img, nome_arquivo)
        return caminho

    def gerar_qr_degrade(self, data, nome_arquivo="registro_degrade.png"):
        """Gera um QR code com degradê colorido"""
        qr = qrcode.make(data).convert("RGBA")
        width, height = qr.size
        gradient = Image.new("RGBA", qr.size)

        # Criar gradiente de vermelho para azul
        for x in range(width):
            for y in range(height):
                r = int(255 * (x / width))
                b = 255 - r
                gradient.putpixel((x, y), (r, 0, b, 255))

        # Aplicar gradiente apenas nas partes pretas do QR
        pixels_qr = qr.load()
        pixels_grad = gradient.load()
        for x in range(width):
            for y in range(height):
                if pixels_qr[x, y][0] > 128:  # Partes brancas ficam transparentes
                    pixels_grad[x, y] = (255, 255, 255, 0)

        caminho = self._salvar_qr(gradient, nome_arquivo)
        return caminho

    def gerar_qr_codes_completos(self, url_registro, chave_comerciante):
        """Gera os dois QR codes: registro (degradê) e comerciante (padrão)"""
        # QR do registro com degradê
        caminho_registro = self.gerar_qr_degrade(url_registro, "registro_degrade.png")

        # QR da chave do comerciante padrão
        caminho_comerciante = self.gerar_qr_padrao(chave_comerciante, "comerciante_chave.png")

        print(f"QR codes salvos em Backend/static/qrcodes:")
        print(f"- Registro (degradê): {caminho_registro}")
        print(f"- Comerciante (padrão): {caminho_comerciante}")

        return {
            'registro': caminho_registro,
            'comerciante': caminho_comerciante
        }

    def obter_caminho_absoluto(self, caminho_relativo, base_app_dir):
        """Converte caminho relativo para absoluto baseado no diretório da aplicação"""
        return os.path.join(base_app_dir, caminho_relativo)