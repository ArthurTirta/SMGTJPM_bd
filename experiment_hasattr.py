class Product:
    def __init__(self, name, price):
        self.name = name
        self.price = price

class Part:
    def __init__(self, function_call=None, text=None):
        if function_call:
            self.function_call = function_call
        if text:
            self.text = text

def experiment():
    print("--- Eksperimen 1: Objek Sederhana ---")
    p = Product("Jeans", 500000)
    
    # Memeriksa atribut yang ada
    if hasattr(p, 'name'):
        print(f"Objek p punya atribut 'name': {p.name}")
    
    # Memeriksa atribut yang tidak ada
    if not hasattr(p, 'discount'):
        print("Objek p TIDAK punya atribut 'discount'")

    print("\n--- Eksperimen 2: Objek Dinamis (seperti di main.py) ---")
    # Part 1 hanya punya function_call
    part1 = Part(function_call={"name": "get_data", "args": {}})
    # Part 2 hanya punya text
    part2 = Part(text="Halo, apa kabar?")

    parts = [part1, part2]

    for i, part in enumerate(parts):
        print(f"\nMemeriksa Part {i+1}:")
        
        # Cara kerja hasattr:
        if hasattr(part, 'function_call'):
            print(f"- Punya function_call: {part.function_call}")
        else:
            print("- TIDAK punya function_call")

        if hasattr(part, 'text'):
            print(f"- Punya text: {part.text}")
        else:
            print("- TIDAK punya text")

    print("\n--- Eksperimen 3: Penggunaan dalam 'if' (seperti di main.py) ---")
    # if hasattr(part, 'attr') and part.attr:
    # Ini berguna untuk memastikan atribut ADA dan nilainya TIDAK kosong/None
    
    part3 = Part(function_call=None) # function_call ada tapi nilainya None (tergantung implementasi class)
    # Jika kita gunakan: if hasattr(part3, 'function_call') and part3.function_call:
    # Dia akan bernilai False jika part3.function_call adalah None
    
    if hasattr(part1, 'function_call') and part1.function_call:
        print("Part 1 valid untuk diproses (ada atribut dan ada nilainya)")

if __name__ == "__main__":
    experiment()