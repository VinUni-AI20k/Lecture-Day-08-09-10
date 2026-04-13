import os

data_dir = "../data/docs"
files = os.listdir(data_dir)

total_chars = 0
file_count = 0

for file_name in files:
    file_path = os.path.join(data_dir, file_name)
    
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
            char_count = len(text)
            
            total_chars += char_count
            file_count += 1
            
            print(f"{file_name}: {char_count} chars")

print(f"\nSUM: {total_chars} chars")

avg_chars = total_chars / file_count
avg_tokens = avg_chars / 4

chunk_size = int(avg_tokens * 0.5)
chunk_size = max(150, min(chunk_size, 400))
chunk_overlap = int(chunk_size * 0.2)

print(f"Avg chars/file: {avg_chars:.0f}")
print(f"Estimated tokens/file: {avg_tokens:.0f}")
print(f"CHUNK_SIZE: {chunk_size}")
print(f"CHUNK_OVERLAP: {chunk_overlap}")