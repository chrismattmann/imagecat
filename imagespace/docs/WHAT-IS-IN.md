# ImageSpace: what is in, what is out

ImageSpace is the analyst desktop for ImageCat and lives in this RADiX
tree (`imagespace/`). Solr holds OCR and Tika metadata; this app searches
it and shows the pictures.

## Keep

- Solr `imagecat` as the catalog (`id`, `ocr_text`, Tika EXIF, `sha1sum_s_md`)
- Search box = OCR / metadata; `*` = browse
- Image grid
- Detective tray of saved images
- Details: full Tika record + thumbnail; click a field value to search Solr for it
- Images on disk at the Solr `id` path

## Throw out

- Girder 1.x, Mongo, Jade / Backbone / Grunt
- Kitware SMQTK (CaffeNet, FLANN, libSVM, IQR Flask)
- CMU Caffe fg/bg + ScalableLSH
- OpenCV histogram / Tangelo FLANN server
- Docker-as-install
- Columbia / Georgetown / weapons / VideoSpace (not v1)

## Replace

| Was | Is |
| --- | --- |
| Girder plugin | Vue 3 + FastAPI |
| Solr 4 `imagecatdev` | ImageCat Solr 10 `imagecat` |
| Caffe AlexNet FC7 | HuggingFace CLIP (`openai/clip-vit-base-patch32`, Torch) |
| FLANN / ITQ-LSH | Cosine over L2-normalized CLIP vectors (numpy; FAISS when the corpus is huge) |
| SMQTK IQR + libSVM | Tiny Keras head on CLIP vectors |
| CMU Caffe segmentation | U2-Net (`rembg`) fg/bg CLIP indexes |
| Girder Private folder | `localStorage` tray |

Vision transformers stay on Torch + HuggingFace, same as ImageCat TrOCR.
The IQR ranker is a small Keras dense head, not a second vision stack.
