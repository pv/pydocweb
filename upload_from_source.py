import numpydoc as nd

dm = nd.DocModificator('http://127.0.0.1:8000/NumpyDoc','../../numpy')
dm.upload_to_wiki()
