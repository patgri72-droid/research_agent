import re
from datetime import datetime
from fpdf import FPDF


FONT = "main"
FARGE_MRK_BLA = (20, 20, 80)
FARGE_BLA = (40, 40, 130)
FARGE_GRA = (100, 100, 100)
FARGE_GRON = (0, 100, 50)
FARGE_ROD = (160, 40, 40)
FARGE_LILLA = (100, 0, 120)


class RapportPDF(FPDF):
    def __init__(self, tittel: str):
        super().__init__()
        self._tittel = tittel[:70]
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(20, 25, 20)
        # Calibri støtter full Unicode inkl. norske tegn og spesialtegn
        self.add_font("main", "",  "C:/Windows/Fonts/calibri.ttf")
        self.add_font("main", "B", "C:/Windows/Fonts/calibrib.ttf")
        self.add_font("main", "I", "C:/Windows/Fonts/calibrii.ttf")

    def header(self):
        self.set_font(FONT, "I", 8)
        self.set_text_color(*FARGE_GRA)
        self.cell(0, 6, self._tittel, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(210, 210, 210)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font(FONT, "I", 8)
        self.set_text_color(*FARGE_GRA)
        self.cell(0, 8, f"Side {self.page_no()}", align="C")

    def forside(self, dato: str):
        self.add_page()
        self.ln(50)
        self.set_font(FONT, "B", 26)
        self.set_text_color(*FARGE_MRK_BLA)
        self.multi_cell(0, 13, self._tittel, align="C")
        self.ln(10)
        self.set_draw_color(*FARGE_BLA)
        self.set_line_width(0.5)
        self.line(50, self.get_y(), 160, self.get_y())
        self.ln(8)
        self.set_font(FONT, "", 11)
        self.set_text_color(*FARGE_GRA)
        self.cell(0, 7, dato, align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "Generert av Research Agent Team", align="C")
        self.set_line_width(0.2)

    def seksjons_tittel(self, tekst: str):
        self.add_page()
        self.ln(2)
        self.set_font(FONT, "B", 18)
        self.set_text_color(*FARGE_MRK_BLA)
        self.cell(0, 10, tekst, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*FARGE_BLA)
        self.set_line_width(0.4)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_line_width(0.2)
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def _skriv_inline(self, tekst: str, size: int, grunnstil: str = ""):
        deler = re.split(r'\*\*(.+?)\*\*', tekst)
        for i, del_tekst in enumerate(deler):
            stil = "B" if i % 2 == 1 else grunnstil
            self.set_font(FONT, stil, size)
            if del_tekst:
                self.write(5, del_tekst)

    def skriv_markdown(self, tekst: str):
        for linje in tekst.split("\n"):
            linje = linje.rstrip()

            if linje.startswith("## "):
                self.ln(4)
                self.set_font(FONT, "B", 13)
                self.set_text_color(*FARGE_BLA)
                self.multi_cell(0, 7, linje[3:])
                self.set_draw_color(180, 190, 220)
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(3)
                self.set_text_color(0, 0, 0)

            elif linje.startswith("### "):
                self.ln(3)
                self.set_font(FONT, "B", 11)
                self.set_text_color(40, 40, 40)
                self.multi_cell(0, 6, linje[4:])
                self.ln(1)
                self.set_text_color(0, 0, 0)

            elif linje.startswith("- ") or linje.startswith("* "):
                self.set_x(26)
                self.set_font(FONT, "", 10)
                self.write(5, "-  ")
                self._skriv_inline(linje[2:], 10)
                self.ln(5)

            elif linje.strip() == "---":
                self.ln(2)
                self.set_draw_color(200, 200, 200)
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(4)

            elif linje.strip() == "":
                self.ln(3)

            else:
                self._skriv_inline(linje, 10)
                self.ln(5)

    def fargede_punkter(self, tittel: str, elementer: list, farge: tuple):
        if not elementer:
            return
        self.ln(2)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*farge)
        self.cell(0, 7, tittel, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(30, 30, 30)
        self.set_font(FONT, "", 10)
        for elem in elementer:
            self.set_x(26)
            self.write(5, "-  ")
            self.multi_cell(0, 5, elem)
            self.ln(1)
        self.ln(3)


def generer_pdf(tema: str, research: dict, analyse: dict = None,
                plan: str = None, output_path: str = None) -> str:
    """Bygger PDF-en. Analyse- og handlingsplan-seksjonene tas bare med
    hvis de finnes (de kan være avskrudd i konfigurasjonen)."""
    dato = datetime.now().strftime("%d.%m.%Y %H:%M")
    pdf = RapportPDF(tema)

    # Forside
    pdf.forside(dato)

    # Forskningsrapport
    pdf.seksjons_tittel("Forskningsrapport")
    pdf.skriv_markdown(research.get("rapport", ""))

    # Analyse (valgfri)
    if analyse:
        pdf.seksjons_tittel("Analyse")
        pdf.fargede_punkter("Mønstre og tendenser", analyse.get("mønstre", []), FARGE_BLA)
        pdf.fargede_punkter("Nøkkelfakta", analyse.get("nøkkelfakta", []), FARGE_GRON)
        pdf.fargede_punkter("Usikkerhet og risiko", analyse.get("usikkerhet", []), FARGE_ROD)
        pdf.fargede_punkter("Kunnskapshull", analyse.get("kunnskapshull", []), FARGE_LILLA)

        styrke = analyse.get("grunnlag_styrke", "ukjent").upper()
        pdf.set_font(FONT, "B", 10)
        pdf.set_text_color(*FARGE_MRK_BLA)
        pdf.cell(0, 6, f"Grunnlagsstyrke: {styrke}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT, "I", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, analyse.get("sammendrag", ""))

    # Handlingsplan (valgfri)
    if plan:
        pdf.seksjons_tittel("Handlingsplan")
        pdf.skriv_markdown(plan)

    pdf.output(output_path)
    return output_path
