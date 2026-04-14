import chromadb
print("ChromaDB imported")
client = chromadb.PersistentClient(path='./test_chroma')
print("Client created")
col = client.get_or_create_collection('test_col')
print("Collection created")
