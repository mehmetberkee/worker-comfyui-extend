# ExtendPro API Reference

RunPod Serverless endpoint üzerinden ComfyUI workflow'larını çalıştırmak için kullanılan API dokümantasyonu.

---

## Endpoint Bilgileri

| Alan | Değer |
|------|-------|
| Base URL | `https://api.runpod.ai/v2/{ENDPOINT_ID}` |
| Auth Header | `Authorization: Bearer {RUNPOD_API_KEY}` |
| Content-Type | `application/json` |

### Kullanılabilir Endpoint'ler

| Method | Path | Açıklama |
|--------|------|----------|
| POST | `/run` | Asenkron iş başlatır. Job ID döner, sonucu `/status/{id}` ile sorgularsın. |
| POST | `/runsync` | Senkron iş başlatır. Sonuç doğrudan response'ta döner (timeout riski var). |
| GET | `/status/{job_id}` | Asenkron işin durumunu ve sonucunu sorgular. |

> **Öneri:** Uzun süren generation işleri için `/run` + `/status` polling kullanın. `/runsync` timeout olabilir.

---

## Request Body Yapısı

```json
{
  "input": {
    "workflow": { ... },
    "images": [
      {
        "name": "dosya_adi.png",
        "image": "base64_encoded_string"
      }
    ],
    "prompt": "optional - CLIPTextEncode text override",
    "image_name": "optional - LoadImage node override",
    "workflow_overrides": [
      {
        "node_id": "156",
        "input_name": "seed",
        "value": 123456
      }
    ]
  }
}
```

### `input` Alanları

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| `workflow` | object | Evet | ComfyUI API format workflow JSON |
| `images` | array | Hayır | Upload edilecek görseller (base64) |
| `prompt` | string | Hayır | İlk bulunan CLIPTextEncode (Positive Prompt) node'unun text'ini override eder |
| `image_name` | string | Hayır | İlk bulunan LoadImage node'unun image input'unu override eder |
| `workflow_overrides` | array | Hayır | Herhangi bir node'un herhangi bir input'unu override etmek için |

### `images` Array Item Yapısı

| Alan | Tip | Açıklama |
|------|-----|----------|
| `name` | string | Dosya adı (workflow'daki node'larda referans edilen isimle aynı olmalı) |
| `image` | string | Base64 encoded görsel. Data URI prefix (`data:image/png;base64,`) desteklenir, otomatik temizlenir. |

### `workflow_overrides` Array Item Yapısı

| Alan | Tip | Açıklama |
|------|-----|----------|
| `node_id` | string | Hedef node ID (workflow JSON'daki key) |
| `input_name` | string | Override edilecek input adı |
| `value` | any | Yeni değer |

---

## Workflow: ExtendPro v3

Bu workflow, bir görseli mask ile inpainting/outpainting yaparak genişletir.

### Genel Akış

```
LoadImage (173) ──→ ImageScale ──→ VAEEncode ──→ ReferenceLatent ──→ LanPaint_KSampler ──→ VAEDecode ──→ SaveImage
                                                       ↑                      ↑
LoadImageMask (169) ──→ ResizeImageMask ──→ SetLatentNoiseMask ──────────────┘
                                                       ↑
CLIPTextEncode (107) ──→ FluxGuidance ────────────────┘
```

### Kritik Node'lar

| Node ID | Class Type | Rolü |
|---------|-----------|------|
| **173** | `LoadImage` | Ana görsel (inpaint edilecek görsel) |
| **169** | `LoadImageMask` | Mask görsel (beyaz=inpaint edilecek alan, siyah=korunacak alan) |
| **107** | `CLIPTextEncode` | Positive prompt - oluşturulacak içeriği tanımlar |
| **156** | `LanPaint_KSampler` | Sampler ayarları (seed, steps, cfg, denoise) |
| **126** | `UNETLoader` | Diffusion model (`flux-2-klein-9b.safetensors`) |
| **146** | `CLIPLoader` | CLIP model (`qwen_3_8b.safetensors`) |
| **161** | `LoraLoader` | LoRA (`pro_extend_000002000.safetensors`) |
| **102** | `VAELoader` | VAE (`flux2-vae.safetensors`) |
| **135** | `PrimitiveFloat` | Megapixel ayarı (default: 1) |

### Gerekli Modeller (Docker İmajında Yüklü Olmalı)

| Model | Tip | Path |
|-------|-----|------|
| `flux-2-klein-9b.safetensors` | UNET | `models/diffusion_models/` |
| `qwen_3_8b.safetensors` | CLIP | `models/clip/` |
| `pro_extend_000002000.safetensors` | LoRA | `models/loras/` |
| `flux2-vae.safetensors` | VAE | `models/vae/` |

### Gerekli Custom Node'lar

| Node Paketi | Sağladığı Node'lar |
|------------|-------------------|
| [LanPaint](https://github.com/scraed/LanPaint) | `LanPaint_KSampler`, `ReferenceLatent` |
| [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) | `Image Comparer (rgthree)` |
| ComfyUI Built-in | Diğer tüm node'lar |

---

## Görsel Girdiler

### Ana Görsel (Node 173 - LoadImage)

- Inpaint/outpaint edilecek kaynak görsel
- Mask ile birlikte kullanılır
- Workflow otomatik olarak uygun boyuta scale eder

### Mask Görsel (Node 169 - LoadImageMask)

- Alpha channel kullanılır (`channel: "alpha"`)
- **Beyaz alan** = AI tarafından doldurulacak (inpaint edilecek)
- **Siyah alan** = Korunacak (dokunulmayacak)
- Mask isimleri: `mask_left.png`, `mask_right.png`, `mask_top.png`, `mask_bottom.png` vb.

---

## Web App Entegrasyonu

### Minimum İstek Oluşturma (JavaScript)

```javascript
async function generateExtendPro({ imageFile, maskFile, prompt, seed }) {
  // Görselleri base64'e çevir
  const imageBase64 = await fileToBase64(imageFile);
  const maskBase64 = await fileToBase64(maskFile);

  // Workflow template'i yükle
  const workflow = structuredClone(EXTENDPRO_WORKFLOW);

  // Dinamik değerleri set et
  workflow["173"].inputs.image = "input_image.png";
  workflow["169"].inputs.image = "input_mask.png";
  workflow["107"].inputs.text = prompt;
  workflow["156"].inputs.seed = seed ?? Math.floor(Math.random() * 2 ** 53);

  const requestBody = {
    input: {
      workflow,
      images: [
        { name: "input_image.png", image: imageBase64 },
        { name: "input_mask.png", image: maskBase64 }
      ]
    }
  };

  return requestBody;
}

// Helper: File → base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
```

### Alternatif: workflow_overrides Kullanımı

Workflow'u olduğu gibi gönderip sadece belirli değerleri override edebilirsiniz:

```javascript
const requestBody = {
  input: {
    workflow: EXTENDPRO_WORKFLOW,
    images: [
      { name: "input_image.png", image: imageBase64 },
      { name: "input_mask.png", image: maskBase64 }
    ],
    prompt: "Fill the empty space with a beautiful sunset...",
    workflow_overrides: [
      { node_id: "156", input_name: "seed", value: 42 },
      { node_id: "135", input_name: "value", value: 1.5 },
      { node_id: "100", input_name: "guidance", value: 6 }
    ]
  }
};
```

### API Çağrısı (Async Flow - Önerilen)

```javascript
const RUNPOD_API_KEY = "rpa_...";
const ENDPOINT_ID = "your_endpoint_id";
const BASE_URL = `https://api.runpod.ai/v2/${ENDPOINT_ID}`;

// 1. İşi başlat
async function startJob(requestBody) {
  const res = await fetch(`${BASE_URL}/run`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RUNPOD_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(requestBody)
  });
  const data = await res.json();
  return data.id; // job ID
}

// 2. Sonucu polling ile bekle
async function pollResult(jobId, intervalMs = 3000, maxAttempts = 60) {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`${BASE_URL}/status/${jobId}`, {
      headers: { "Authorization": `Bearer ${RUNPOD_API_KEY}` }
    });
    const data = await res.json();

    if (data.status === "COMPLETED") {
      return data.output;
    }
    if (data.status === "FAILED") {
      throw new Error(data.error || "Job failed");
    }

    // IN_QUEUE veya IN_PROGRESS - bekle
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error("Polling timeout");
}

// 3. Tam akış
async function generate(imageFile, maskFile, prompt) {
  const requestBody = await generateExtendPro({
    imageFile, maskFile, prompt
  });

  const jobId = await startJob(requestBody);
  console.log("Job started:", jobId);

  const output = await pollResult(jobId);
  console.log("Job completed!");

  // output.images[0].data → base64 encoded PNG
  const imgSrc = `data:image/png;base64,${output.images[0].data}`;
  return imgSrc;
}
```

---

## Response Yapısı

### Başarılı Response

```json
{
  "id": "job-id-here",
  "status": "COMPLETED",
  "delayTime": 5000,
  "executionTime": 90000,
  "output": {
    "images": [
      {
        "filename": "Flux2_dev_00001_.png",
        "type": "base64",
        "data": "iVBORw0KGgo..."
      }
    ]
  }
}
```

### Hatalı Response

```json
{
  "id": "job-id-here",
  "status": "FAILED",
  "error": "Workflow validation failed:\n• Node 102 (errors): ..."
}
```

### Output Image Tipleri

| `type` | Açıklama |
|--------|----------|
| `base64` | PNG görseli base64 encoded (varsayılan) |
| `s3_url` | S3 bucket URL'i (eğer `BUCKET_ENDPOINT_URL` env var ayarlanmışsa) |

---

## Ayarlanabilir Parametreler (Sık Kullanılan Override'lar)

| Node ID | Input | Default | Açıklama |
|---------|-------|---------|----------|
| `156` | `seed` | random | Üretim seed'i. Aynı seed + aynı input = aynı sonuç |
| `156` | `steps` | 4 | Sampling adım sayısı. Arttırılırsa kalite artar ama yavaşlar |
| `156` | `denoise` | 1 | Denoise gücü (0-1). 1=tam inpaint, düşük=orijinale yakın |
| `100` | `guidance` | 4 | Prompt'a ne kadar sadık kalınsın (düşük=serbest, yüksek=prompt'a bağlı) |
| `135` | `value` | 1 | Çıktı megapiksel (1=~1MP, arttırılırsa çözünürlük artar) |
| `107` | `text` | (prompt) | Positive prompt - ne üretileceğini açıklar |

---

## Tipik İş Akışı Süreleri

| Durum | Süre |
|-------|------|
| Cold start (worker uyandırma) | ~5-30 sn |
| Warm worker (kuyruk boş) | ~1-5 sn delay |
| Generation (1MP, 4 steps) | ~10-100 sn |

> Süre; görsel boyutu, step sayısı ve GPU tipine göre değişir.

---

## Hata Durumları ve Çözümleri

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `value_not_in_list` | Model dosyası worker'da yok | Docker imajına modeli ekle |
| `request does not exist` | Job ID expire olmuş | Yeni istek at, polling interval'i kısalt |
| `IN_PROGRESS` timeout | runsync timeout | `/run` + `/status` polling kullan |
| `Failed to upload image` | Base64 encoding hatalı | Data URI prefix'i kontrol et |
| `Missing 'workflow' parameter` | Request body yapısı hatalı | `input.workflow` key'ini kontrol et |
