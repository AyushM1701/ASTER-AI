"""Generate labelled SYNTHETIC handwritten-style prescriptions (no real patients).

    python evaluation/handwriting/make_synthetic.py --fonts D:/aster-eval/handwriting/fonts --out D:/aster-eval/handwriting/set --n 72

Fonts: Google Fonts handwriting families (SIL OFL 1.1). Each image has 1-3 medicine
lines in common Indian/UK/US prescription shorthand, plus distractor header lines;
difficulty varies (font, slant, blur, noise, contrast, rotation). Ground truth is
written beside each image. These are rendered fonts, NOT real handwriting: results
bound performance from above for messy real prescriptions.
"""
import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

MEDICINES = [("Amoxicillin", ["250 mg", "500 mg"]), ("Metronidazole", ["400 mg", "200 mg"]), ("Paracetamol", ["500 mg", "650 mg"]),
             ("Ibuprofen", ["200 mg", "400 mg"]), ("Omeprazole", ["20 mg", "40 mg"]), ("Cetirizine", ["10 mg"]),
             ("Metformin", ["500 mg", "1000 mg"]), ("Amlodipine", ["5 mg", "10 mg"]), ("Azithromycin", ["250 mg", "500 mg"]),
             ("Pantoprazole", ["40 mg"]), ("Diclofenac", ["50 mg"]), ("Doxycycline", ["100 mg"]), ("Clindamycin", ["300 mg"]),
             ("Atorvastatin", ["10 mg", "20 mg"]), ("Chlorhexidine", ["0.2%"])]
FORMS = ["Tab", "Cap"]
FREQUENCIES = ["OD", "BD", "TDS", "1-0-1", "1-1-1", "0-0-1", "twice daily"]
DURATIONS = ["x 3 days", "x 5 days", "x 7 days", "for 5 days", "for 1 week"]
INSTRUCTIONS = ["after food", "before food", "at bedtime", ""]


def line_for(rng):
    name, strengths = rng.choice(MEDICINES)
    strength = rng.choice(strengths)
    form = "Mouthwash" if name == "Chlorhexidine" else rng.choice(FORMS)
    frequency, duration, instruction = rng.choice(FREQUENCIES), rng.choice(DURATIONS), rng.choice(INSTRUCTIONS)
    if name == "Chlorhexidine":
        text = f"{name} {strength} mouthwash 10 ml {frequency} {duration}"
        truth = {"medicine_name": name, "strength": strength, "formulation": "mouthwash", "frequency": frequency, "duration": duration}
    else:
        text = f"{form}. {name} {strength} {frequency} {duration} {instruction}".strip()
        truth = {"medicine_name": name, "strength": strength, "formulation": form, "frequency": frequency, "duration": duration}
    if instruction:
        truth["instructions"] = instruction
    return text, truth


def render(lines, font_path, difficulty, rng):
    width = 1400
    image = Image.new("L", (width, 260 + 120 * len(lines)), 248)
    draw = ImageDraw.Draw(image)
    header = ImageFont.truetype(str(font_path), 44)
    body = ImageFont.truetype(str(font_path), 58 - 6 * difficulty)
    draw.text((60, 40), "Dr. Example Clinic   (synthetic test sheet)", fill=60, font=header)
    draw.text((60, 110), "Rx", fill=30, font=header)
    y = 190
    for text in lines:
        x = 70 + rng.randint(-10, 30)
        draw.text((x, y + rng.randint(-6, 6)), text, fill=rng.randint(10, 60 + 30 * difficulty), font=body)
        y += 110
    if difficulty >= 1:
        image = image.rotate(rng.uniform(-2.5, 2.5) * difficulty, expand=True, fillcolor=248)
    if difficulty >= 2:
        image = image.filter(ImageFilter.GaussianBlur(0.8 * difficulty))
        noise = Image.effect_noise(image.size, 18 * difficulty).point(lambda v: v - 128)
        image = Image.blend(image, noise.convert("L"), 0.08)
    return image.convert("RGB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--n", type=int, default=72)
    args = parser.parse_args()
    rng = random.Random(1015)
    fonts = sorted(Path(args.fonts).glob("*.ttf"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i in range(args.n):
        font = fonts[i % len(fonts)]
        difficulty = (i // len(fonts)) % 3
        items = [line_for(rng) for _ in range(rng.randint(1, 3))]
        image = render([t for t, _ in items], font, difficulty, rng)
        name = f"synthetic-hw-{i:03d}.png"
        image.save(out / name)
        manifest.append({"file": name, "font": font.stem, "difficulty": difficulty, "lines": [t for t, _ in items],
                         "truth": [g for _, g in items], "label_origin": "synthetic_generated"})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(len(manifest), "images")


if __name__ == "__main__":
    main()
