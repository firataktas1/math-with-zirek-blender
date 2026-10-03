"""Math with Zirek: ücretsiz Colab T4 üzerinde yerel video modeli denemesi.

Önce LTX-Video (2B, diffusers), LTX hiç sonuç vermezse Wan 2.1 1.3B. Ücretli API yok, anahtar yok.
Girdi: Video 1'den 5 sn'lik kâğıt kesik bölüm (Zirek ve öğrenci kapının önünde, 3:27).

  python zirek_test.py              sürücü: bütün denemeler sırayla, her biri ayrı süreçte
  python zirek_test.py --tek JSON   tek deneme (sürücü çağırır)
  python zirek_test.py --metin ltx  istem gömmelerini hesapla (sürücü çağırır)

Yerelde sahte deneme (CPU, küçük rastgele modeller, kod yolunu sınamak için): ZIREK_SMOKE=1
"""
import copy, gc, json, os, subprocess, sys, time, traceback
from pathlib import Path

SMOKE = os.environ.get("ZIREK_SMOKE") == "1"
KOK = Path(os.environ.get("ZIREK_KOK", "/content/zirek"))
GIRDI, CIKTI = KOK / "girdi", KOK / "sonuc"
FPS = 24
BUTCE_DK = float(os.environ.get("ZIREK_BUTCE_DK", "75"))      # denemeler için süre sınırı (indirme hariç)
DENEME_ZAMAN_ASIMI_DK = 25                                      # tek denemenin üst sınırı
EN_AZ_AYAR = 3                                                  # bütçe dolsa da bu kadar farklı ayar denenir

LTX_REPO = "Lightricks/LTX-Video-0.9.5"          # T5, belirteçleyici, zamanlayıcı ve yedek model
LTX_DAMITIK = "https://huggingface.co/Lightricks/LTX-Video/blob/main/ltxv-2b-0.9.8-distilled.safetensors"
WAN_T2V_REPO = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
WAN_VACE_REPO = "Wan-AI/Wan2.1-VACE-1.3B-diffusers"

ISTEM = (
    "A 2D paper cut-out animation of two cartoon characters talking in front of a dry stone wall with a "
    "wooden farm gate. On the left, a red panda teacher wearing a black and white checkered Kurdish "
    "headscarf, a grey jacket and a blue patterned sash stands still, blinks and nods gently while "
    "talking. On the right, a young man with black hair and a blue t-shirt listens and smiles. Behind "
    "them are green rolling hills, small stones on the grass and a warm evening sky with paper clouds. "
    "Every shape is cut from textured paper with torn white edges and soft drop shadows between the "
    "layers. Static camera, flat lighting, calm and subtle motion."
)
OLUMSUZ = (
    "worst quality, inconsistent motion, blurry, jittery, distorted, deformed face, morphing, melting, "
    "extra limbs, photorealistic, 3D render, glossy plastic, text, watermark, camera shake"
)

# Çözünürlük merdiveni: 720p'den başla, bellek ya da süre yetmezse küçült (genişlik, yükseklik, kare).
# LTX 32'nin katı ister (720 değil 704); 121 kare = 24 kare/sn'de 5,04 sn.
LTX_MERDIVEN = [("damitik", 1280, 704, 121), ("damitik", 960, 544, 121), ("damitik", 768, 448, 121),
                ("damitik", 768, 448, 73), ("095", 768, 448, 121)]
WAN_MERDIVEN = [(832, 480, 81), (832, 480, 49), (640, 352, 49)]
if SMOKE:
    LTX_MERDIVEN = [("damitik", 64, 64, 17), ("damitik", 64, 32, 9), ("damitik", 32, 32, 9),
                    ("damitik", 32, 32, 9), ("095", 32, 32, 9)]
    WAN_MERDIVEN = [(32, 32, 9), (32, 32, 5), (16, 16, 5)]

# Model türleri: "damitik" = 0.9.8 distilled (8 adım, rehber 1, resmî ayar), "095" = 0.9.5 (yedek: 40 adım, rehber 3)
LTX_TUR = {"damitik": {"adim": 8, "rehber": 1.0}, "095": {"adim": 40, "rehber": 3.0}}
LTX_V2V_SIGMALAR = (0.45, 0.75)   # video-to-video: kaynağa eklenen gürültü (damıtık çizelgede 0,42 = 1 adım, 0,725 = 2 adım)
LTX_KOD_ZAMANI, LTX_KOD_GURULTU = 0.05, 0.025   # VAE çözme ayarları (0.9.8 distilled resmî yapılandırma)
LTX_KOSUL_GURULTU = 0.15          # ilk kare koşuluna eklenen gürültü (resmî inference.py varsayılanı)
# Hassasiyet: T4'te bf16 donanımda yok; LTX'te fp16 bozuk görüntü verebiliyor (Lightricks/LTX-Video#126, ComfyUI
# LTXV için fp16'yı kapatır). Ağırlıklar bf16 saklanır (dosya zaten bf16, kayıpsız), hesap fp32 yapılır.


# ---------------------------------------------------------------- ortak yardımcılar
def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cihaz():
    import torch
    return "cuda" if torch.cuda.is_available() and not SMOKE else "cpu"


def nvrtc_hazirla():
    """Colab CUDA 13 imajında görülen 'libnvrtc-builtins.so.13.0 açılamadı' hatasına karşı (colabtools #6111):
    kütüphane varsa torch'tan önce yüklenir; yoksa hiçbir şey yapmaz."""
    import ctypes, glob
    for yol in glob.glob("/usr/local/lib/python3*/dist-packages/nvidia/cu13/lib/libnvrtc-builtins.so.13*"):
        try:
            ctypes.CDLL(yol)
            return yol
        except OSError:
            pass
    return None


def kirpma_kutusu(w, h, kw=1280, kh=720):
    """kirp()'ın kaynak karede (kw x kh) kullandığı bölge: (x, y, genişlik, yükseklik), kaynak pikselinde."""
    s = max(w / kw, h / kh)
    gw, gh = w / s, h / s
    return [round((kw - gw) / 2, 2), round((kh - gh) / 2, 2), round(gw, 2), round(gh, 2)]


def kirp(img, w, h):
    """Kareyi en-boy oranını bozmadan w x h'yi kaplayacak kadar ölçekler, ortadan keser."""
    from PIL import Image
    s = max(w / img.width, h / img.height)
    yeni = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
    x, y = (yeni.width - w) // 2, (yeni.height - h) // 2
    return yeni.crop((x, y, x + w, y + h))


def girdi_kareleri(w, h, n, fps=FPS):
    """Girdi klibi 24 kare/sn; fps farklıysa (Wan 16) kareler zamana göre seçilir."""
    import imageio.v2 as iio
    from PIL import Image
    r = iio.get_reader(str(GIRDI / "zirek_klip.mp4"))
    tum = [k for k in r]
    r.close()
    sira = [int(i * FPS / fps + 0.5) for i in range(n)]
    if sira[-1] >= len(tum):
        raise RuntimeError(f"girdi klibinde {len(tum)} kare var, {sira[-1] + 1} gerekiyordu")
    return [kirp(Image.fromarray(tum[i]).convert("RGB"), w, h) for i in sira]


def girdi_karesi(w, h):
    from PIL import Image
    return kirp(Image.open(GIRDI / "zirek_kare.png").convert("RGB"), w, h)


class BozukCikti(Exception):
    pass


def denetle(kareler):
    """kareler: numpy (F, H, W, 3), 0..1. NaN, sonsuz ya da düz renk (siyah/gri) çıktıyı yakalar."""
    import numpy as np
    if not np.isfinite(kareler).all():
        raise BozukCikti("çıktıda NaN ya da sonsuz değer var")
    ort, sap = float(kareler.mean()), float(kareler.std())
    if sap < 0.01:
        raise BozukCikti(f"çıktı düz renk (ortalama {ort:.3f}, sapma {sap:.4f})")
    return {"ortalama": round(ort, 4), "sapma": round(sap, 4)}


def nan_bekcisi(pipe, adim, t, kw):
    """Her adımda gizli temsili denetler; NaN görülürse boşuna beklemeden durur."""
    import torch
    if not torch.isfinite(kw["latents"]).all():
        raise BozukCikti(f"{adim}. adımda gizli temsilde NaN/sonsuz değer (fp16 taşması)")
    return kw


def video_yaz(kareler_np, yol, fps=FPS):
    """kareler_np: (F, H, W, 3) float 0..1. Tek kodlama, H.264 CRF 12."""
    import imageio.v2 as iio
    import numpy as np
    k8 = (np.clip(kareler_np, 0, 1) * 255).round().astype("uint8")
    w = iio.get_writer(str(yol), fps=fps, codec="libx264", quality=None, pixelformat="yuv420p",
                       macro_block_size=1 if SMOKE else 16, output_params=["-crf", "12", "-preset", "medium"])
    for k in k8:
        w.append_data(k)
    w.close()
    # hızlı bakış için 6 karelik şerit
    from PIL import Image
    secilen = [k8[i] for i in np.linspace(0, len(k8) - 1, 6).round().astype(int)]
    serit = Image.fromarray(np.concatenate(secilen, axis=1))
    if serit.width > 3000:
        serit = serit.resize((3000, round(serit.height * 3000 / serit.width)))
    serit.save(str(yol).replace(".mp4", "-serit.jpg"), quality=90)


# ---------------------------------------------------------------- sahte (küçük) modeller: yalnız ZIREK_SMOKE=1
def sahte_t5():
    from transformers import AutoConfig, AutoTokenizer, T5EncoderModel
    cfg = AutoConfig.from_pretrained("hf-internal-testing/tiny-random-t5")
    return T5EncoderModel(cfg).eval(), AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-t5")


def sahte_ltx():
    import torch
    from diffusers import AutoencoderKLLTXVideo, FlowMatchEulerDiscreteScheduler, LTXVideoTransformer3DModel
    torch.manual_seed(0)
    tr = LTXVideoTransformer3DModel(in_channels=8, out_channels=8, patch_size=1, patch_size_t=1,
                                    num_attention_heads=4, attention_head_dim=8, cross_attention_dim=32,
                                    num_layers=1, caption_channels=32)
    vae = AutoencoderKLLTXVideo(in_channels=3, out_channels=3, latent_channels=8, block_out_channels=(8, 8, 8, 8),
                                decoder_block_out_channels=(8, 8, 8, 8), layers_per_block=(1, 1, 1, 1, 1),
                                decoder_layers_per_block=(1, 1, 1, 1, 1),
                                spatio_temporal_scaling=(True, True, False, False),
                                decoder_spatio_temporal_scaling=(True, True, False, False),
                                decoder_inject_noise=(False, False, False, False, False),
                                upsample_residual=(False, False, False, False), upsample_factor=(1, 1, 1, 1),
                                timestep_conditioning=True, patch_size=1, patch_size_t=1,
                                encoder_causal=True, decoder_causal=False)
    return tr, vae, FlowMatchEulerDiscreteScheduler()


# ---------------------------------------------------------------- istem gömmeleri (T5 bir kez, sonra bellekten çıkar)
def sdpa_yokla():
    """fp32 bellek-verimli dikkat T4'te çalışıyor mu, hızı ne? (yoksa bütün LTX denemeleri bellekten düşer)"""
    import torch
    import torch.nn.functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel
    sonuc = {}
    try:
        q = torch.randn(1, 32, 14080, 64, device="cuda")
        with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION):
            F.scaled_dot_product_attention(q, q, q)
            torch.cuda.synchronize()
            t0 = time.time()
            for _ in range(3):
                F.scaled_dot_product_attention(q, q, q)
            torch.cuda.synchronize()
        sure = (time.time() - t0) / 3
        sonuc = {"verimli_dikkat_fp32": "çalışıyor", "sn_14080_belirtec": round(sure, 3),
                 "tflops": round(4 * 32 * 14080 ** 2 * 64 / sure / 1e12, 2)}
        del q
        torch.cuda.empty_cache()
    except Exception as e:
        sonuc = {"verimli_dikkat_fp32": f"çalışmıyor: {type(e).__name__}: {str(e)[:300]}"}
    (KOK / "sdpa.json").write_text(json.dumps(sonuc, ensure_ascii=False), encoding="utf-8")
    log("SDPA yoklaması:", sonuc)


def metin_gomme(model):
    import torch
    dev = cihaz()
    if model == "ltx" and dev == "cuda":
        sdpa_yokla()
    if SMOKE:
        te, tok = sahte_t5()
    else:
        from transformers import AutoTokenizer, T5EncoderModel, UMT5EncoderModel
        # Wan: VACE deposundaki UMT5 (bf16, 11,4 GB) T2V deposundakiyle aynı ağırlık, yarı boyutta
        repo = LTX_REPO if model == "ltx" else WAN_VACE_REPO
        sinif = T5EncoderModel if model == "ltx" else UMT5EncoderModel
        log(f"metin kodlayıcı yükleniyor ({repo}, fp16, doğrudan GPU'ya)")
        te = sinif.from_pretrained(repo, subfolder="text_encoder", dtype=torch.float16, device_map=dev).eval()
        tok = AutoTokenizer.from_pretrained(repo, subfolder="tokenizer")
    uzunluk = 256 if model == "ltx" else 512
    sonuc = {}
    for ad, metin in (("olumlu", ISTEM), ("olumsuz", OLUMSUZ)):
        if model == "wan":   # Wan boru hattı istemi böyle temizler (ftfy + boşluk)
            from diffusers.pipelines.wan.pipeline_wan import prompt_clean
            metin = prompt_clean(metin)
        t = tok([metin], padding="max_length", max_length=uzunluk, truncation=True,
                add_special_tokens=True, return_tensors="pt")
        maske = t.attention_mask.bool().to(dev)
        with torch.no_grad():
            g = te(t.input_ids.to(dev), attention_mask=maske)[0]
        if model == "wan":   # Wan: dolgu konumları sıfırlanır (pipeline_wan _get_t5_prompt_embeds ile aynı)
            n = int(maske.sum())
            g = torch.cat([g[:, :n], g.new_zeros(1, uzunluk - n, g.size(-1))], dim=1)
        if not torch.isfinite(g).all():
            raise BozukCikti(f"{model} metin gömmesinde NaN/sonsuz değer")
        sonuc[ad] = g.to("cpu", torch.float16)
        sonuc[ad + "_maske"] = maske.to("cpu")
        log(f"{ad}: {int(maske.sum())} belirteç, boyut {tuple(g.shape)}")
    torch.save(sonuc, KOK / f"gomme_{model}.pt")


# ---------------------------------------------------------------- LTX-Video
def ltx_boru(tur):
    import torch
    from diffusers import AutoencoderKLLTXVideo, LTXConditionPipeline, LTXVideoTransformer3DModel
    dev = cihaz()
    if SMOKE:
        tr, vae, sch = sahte_ltx()
        tr.to(dev, torch.float32)
        vae.to(dev, torch.float32)
        pipe = LTXConditionPipeline(scheduler=sch, vae=vae, text_encoder=None, tokenizer=None, transformer=tr)
    else:
        # Ağırlıklar doğrudan GPU'ya yüklenir (Colab'ın ~12,7 GB sistem belleği iki fp32 modeli birden taşımaz).
        # Dönüştürücü fp32 yüklenip hemen bf16 saklamaya çevrilir, VAE ondan sonra gelir: GPU tepe ~12,7 GB.
        if tur == "damitik":
            log("LTX 0.9.8 distilled tek dosyadan yükleniyor (6,3 GB)")
            tr = LTXVideoTransformer3DModel.from_single_file(LTX_DAMITIK, config=LTX_REPO, subfolder="transformer",
                                                             dtype=torch.float32, device=dev)
        else:
            log("LTX 0.9.5 yükleniyor")
            tr = LTXVideoTransformer3DModel.from_pretrained(LTX_REPO, subfolder="transformer", dtype=torch.bfloat16)
            tr.to(dev, torch.float32)
        tr.enable_layerwise_casting(storage_dtype=torch.bfloat16, compute_dtype=torch.float32)
        torch.cuda.empty_cache()
        if tur == "damitik":
            vae = AutoencoderKLLTXVideo.from_single_file(LTX_DAMITIK, config=LTX_REPO, subfolder="vae",
                                                         dtype=torch.float32, device=dev)
        else:
            vae = AutoencoderKLLTXVideo.from_pretrained(LTX_REPO, subfolder="vae", dtype=torch.float32).to(dev)
        pipe = LTXConditionPipeline.from_pretrained(LTX_REPO, transformer=tr, vae=vae, text_encoder=None,
                                                    tokenizer=None)
    # Dönüştürücü: bf16 sakla, fp32 hesapla (norm/proj katmanları fp32 kalır). VAE tamamen fp32.
    if SMOKE:
        pipe.transformer.enable_layerwise_casting(storage_dtype=torch.bfloat16, compute_dtype=torch.float32)
    pipe.to(dev)
    pipe.vae.enable_tiling()
    pipe.vae.use_framewise_decoding = True     # zamanda da parça parça çöz (bellek)
    return pipe


def ltx_coz(pipe, gizli, uretec):
    """output_type='latent' ile dönen gizli temsili fp32 VAE ile çözer (boru hattının çözme adımının aynısı)."""
    import torch
    from diffusers.utils.torch_utils import randn_tensor
    vae = pipe.vae
    g = pipe._denormalize_latents(gizli.float(), vae.latents_mean, vae.latents_std, vae.config.scaling_factor)
    g = g.to(vae.dtype)
    t = None
    if vae.config.timestep_conditioning:
        gurultu = randn_tensor(g.shape, generator=uretec, device=g.device, dtype=g.dtype)
        t = torch.tensor([LTX_KOD_ZAMANI], device=g.device, dtype=g.dtype)
        s = torch.tensor([LTX_KOD_GURULTU], device=g.device, dtype=g.dtype)[:, None, None, None, None]
        g = (1 - s) * g + s * gurultu
    with torch.no_grad():
        video = vae.decode(g, t, return_dict=False)[0].cpu()
    return pipe.video_processor.postprocess_video(video.float(), output_type="np")[0]


def ltx_v2v_gucu(pipe, adim, hedef_sigma):
    """denoise_strength adım sayısıyla keser; hedef gürültü düzeyine (sigma) karşılık gelen değeri bulur."""
    from diffusers.pipelines.ltx.pipeline_ltx_condition import linear_quadratic_schedule
    sch = copy.deepcopy(pipe.scheduler)
    sch.set_timesteps(timesteps=(linear_quadratic_schedule(adim) * 1000).tolist(), device="cpu")
    sig = sch.sigmas[:-1].tolist()
    i = next((j for j, s in enumerate(sig) if s <= hedef_sigma), adim - 1)
    return (adim - i) / adim + 1e-6, sig[i], adim - i


def ltx_uret(cfg, pipe):
    import torch
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition, retrieve_latents
    w, h, n = cfg["w"], cfg["h"], cfg["kare"]
    dev = cihaz()
    ayar = LTX_TUR[cfg["tur"]]
    adim, rehber = ayar["adim"], ayar["rehber"]
    cfg.update(adim=adim, rehber=rehber)
    gm = torch.load(KOK / "gomme_ltx.pt")
    dt = torch.float32                     # hesap türü (gömmeler dönüştürücü girdisinin türünü belirler)
    ortak = dict(prompt_embeds=gm["olumlu"].to(dev, dt), prompt_attention_mask=gm["olumlu_maske"].to(dev),
                 height=h, width=w, num_frames=n, frame_rate=FPS, guidance_scale=rehber,
                 output_type="latent", callback_on_step_end=nan_bekcisi)
    if rehber > 1:
        ortak.update(negative_prompt_embeds=gm["olumsuz"].to(dev, dt),
                     negative_prompt_attention_mask=gm["olumsuz_maske"].to(dev))
    uretec = torch.Generator(device=dev).manual_seed(cfg.get("tohum", 42))
    if cfg["yol"] == "ltx_i2v":
        kosul = LTXVideoCondition(image=girdi_karesi(w, h), frame_index=0, strength=1.0)
        cikti = pipe(conditions=[kosul], image_cond_noise_scale=LTX_KOSUL_GURULTU, num_inference_steps=adim,
                     generator=uretec, **ortak)
    else:
        # video-to-video: kaynak klip VAE ile kodlanır, hedef sigma kadar gürültülenir, kalan adımlarla yeniden çizilir
        guc, sigma, kalan = ltx_v2v_gucu(pipe, adim, cfg["sigma"])
        cfg.update(denoise_strength=round(guc, 6), gercek_sigma=round(sigma, 4), calisan_adim=kalan)
        log(f"v2v: hedef sigma {cfg['sigma']} -> {sigma:.3f}, {kalan}/{adim} adım")
        onbellek = KOK / f"gizli_{cfg['tur']}_{w}x{h}_{n}.pt"   # iki v2v gücü aynı kodlamayı kullanır
        if onbellek.exists():
            gz = torch.load(onbellek).to(dev)
        else:
            kaynak = pipe.video_processor.preprocess_video(girdi_kareleri(w, h, n), h, w)
            kaynak = kaynak.to(dev, dtype=pipe.vae.dtype)
            with torch.no_grad():
                gz = retrieve_latents(pipe.vae.encode(kaynak), generator=uretec)
            del kaynak
            gz = pipe._normalize_latents(gz, pipe.vae.latents_mean, pipe.vae.latents_std).float()
            torch.save(gz.cpu(), onbellek)
            if dev == "cuda":
                torch.cuda.empty_cache()
        cikti = pipe(latents=gz, denoise_strength=guc, num_inference_steps=adim, image_cond_noise_scale=0.0,
                     generator=uretec, **ortak)
    gizli = cikti.frames
    del cikti
    if dev == "cuda":                       # çözmeden önce dönüştürücüyü GPU'dan çıkar (~3,9 GB yer açar)
        pipe.transformer.to("cpu")
        torch.cuda.empty_cache()
    return ltx_coz(pipe, gizli, uretec)


# ---------------------------------------------------------------- Wan 2.1 1.3B (yalnız LTX hiç sonuç vermezse)
WAN_ADIM, WAN_REHBER, WAN_FPS = 30, 5.0, 16   # Wan 2.1 doğal hızı 16 kare/sn (81 kare = 5,06 sn)


def sahte_wan(vace):
    import torch
    from diffusers import AutoencoderKLWan, UniPCMultistepScheduler, WanTransformer3DModel, WanVACETransformer3DModel
    torch.manual_seed(0)
    vae = AutoencoderKLWan(base_dim=3, z_dim=16, dim_mult=[1, 1, 1, 1], num_res_blocks=1,
                           temperal_downsample=[False, True, True])
    ortak = dict(patch_size=(1, 2, 2), num_attention_heads=2, attention_head_dim=12, in_channels=16,
                 out_channels=16, text_dim=32, freq_dim=256, ffn_dim=32, cross_attn_norm=True,
                 qk_norm="rms_norm_across_heads", rope_max_seq_len=32)
    if vace:
        tr = WanVACETransformer3DModel(num_layers=3, vace_layers=[0, 2], vace_in_channels=96, **ortak)
    else:
        tr = WanTransformer3DModel(num_layers=2, **ortak)
    return tr, vae, UniPCMultistepScheduler(flow_shift=3.0)


def wan_uret(cfg):
    import torch
    from PIL import Image
    vace = cfg["yol"] == "wan_vace_i2v"
    if vace:
        from diffusers import WanVACEPipeline as Boru
    else:
        from diffusers import WanVideoToVideoPipeline as Boru
    if SMOKE:
        tr, vae, sch = sahte_wan(vace)
        pipe = Boru(tokenizer=None, text_encoder=None, transformer=tr, vae=vae, scheduler=sch)
    else:
        # dönüştürücü fp16, VAE fp32 (Wan model kartı); VAE dosyası zaten fp32, fp16'ya hiç yuvarlanmaz
        pipe = Boru.from_pretrained(WAN_VACE_REPO if vace else WAN_T2V_REPO, text_encoder=None, tokenizer=None,
                                    dtype={"default": torch.float16, "vae": torch.float32})
    pipe.vae.to(torch.float32)
    pipe.to(cihaz())
    w, h, n = cfg["w"], cfg["h"], cfg["kare"]
    dev = cihaz()
    gm = torch.load(KOK / "gomme_wan.pt")
    dt = pipe.transformer.dtype
    ortak = dict(prompt_embeds=gm["olumlu"].to(dev, dt), negative_prompt_embeds=gm["olumsuz"].to(dev, dt),
                 height=h, width=w, num_inference_steps=cfg.get("adim", WAN_ADIM), guidance_scale=WAN_REHBER,
                 generator=torch.Generator(device=dev).manual_seed(cfg.get("tohum", 42)), output_type="np",
                 callback_on_step_end=nan_bekcisi)
    if vace:
        # ilk kareden video: ilk kare korunur (maske siyah), kalan kareler üretilir (gri kare, maske beyaz)
        ilk = girdi_karesi(w, h)
        video = [ilk] + [Image.new("RGB", (w, h), (128, 128, 128))] * (n - 1)
        maske = [Image.new("L", (w, h), 0)] + [Image.new("L", (w, h), 255)] * (n - 1)
        cikti = pipe(video=video, mask=maske, num_frames=n, **ortak)
    else:
        cikti = pipe(video=girdi_kareleri(w, h, n, WAN_FPS), strength=cfg.get("guc", 0.5), **ortak)
    return cikti.frames[0]


# ---------------------------------------------------------------- tek deneme (ayrı süreç)
def tek(cfg):
    import torch
    sonuc = dict(cfg)
    sonuc.update(durum="hata", baslangic=time.strftime("%H:%M:%S"))
    t0 = time.time()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        sonuc["gpu"] = torch.cuda.get_device_name(0)
    try:
        if SMOKE and os.environ.get("ZIREK_SMOKE_OOM") == cfg["ad"]:
            raise torch.cuda.OutOfMemoryError("sahte bellek hatası (smoke)")
        if SMOKE and os.environ.get("ZIREK_SMOKE_COKUS") == cfg["ad"]:
            os._exit(137)
        log(f"deneme {cfg['ad']}: {cfg['w']}x{cfg['h']}, {cfg['kare']} kare")
        if cfg["yol"].startswith("ltx"):
            kareler = ltx_uret(sonuc, ltx_boru(cfg["tur"]))
        else:
            kareler = wan_uret(sonuc)
        sonuc["kare_istatistik"] = denetle(kareler)
        yol = CIKTI / f"{cfg['ad']}.mp4"
        sonuc["fps"] = FPS if cfg["yol"].startswith("ltx") else WAN_FPS
        video_yaz(kareler, yol, sonuc["fps"])
        sonuc.update(durum="tamam", dosya=yol.name, cikti_boyut=list(kareler.shape),
                     kaynak_kirpma_1280x720=kirpma_kutusu(cfg["w"], cfg["h"]))
    except torch.cuda.OutOfMemoryError as e:
        sonuc.update(neden="GPU belleği yetmedi", hata=str(e)[:600])
    except BozukCikti as e:
        sonuc.update(neden="bozuk çıktı", hata=str(e))
    except Exception as e:
        ileti = str(e).lower()
        bellek = any(k in ileti for k in ("out of memory", "alloc_failed", "cudnn_status", "32bitindexmath"))
        sonuc.update(neden="GPU belleği yetmedi" if bellek else type(e).__name__,
                     hata=traceback.format_exc()[-2500:])
    sonuc["sure_sn"] = round(time.time() - t0, 1)
    if torch.cuda.is_available():
        sonuc["vram_tepe_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
        sonuc["vram_ayrilan_tepe_gb"] = round(torch.cuda.max_memory_reserved() / 1e9, 2)
    (CIKTI / f"{cfg['ad']}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"deneme {cfg['ad']}: {sonuc['durum']} ({sonuc.get('neden', '')}) {sonuc['sure_sn']} sn")


# ---------------------------------------------------------------- indirme (süreli denemelerin dışında)
def indir(model):
    from huggingface_hub import hf_hub_download, snapshot_download
    t0 = time.time()
    if SMOKE:
        return
    if model == "ltx":
        yollar = [snapshot_download(LTX_REPO, allow_patterns=["text_encoder/*", "tokenizer/*", "scheduler/*",
                                                              "model_index.json", "*/config.json"]),
                  hf_hub_download("Lightricks/LTX-Video", "ltxv-2b-0.9.8-distilled.safetensors")]
    else:
        yollar = [snapshot_download(WAN_VACE_REPO), snapshot_download(WAN_T2V_REPO, ignore_patterns=["text_encoder/*"])]
    boyut = 0
    for y in yollar:
        y = Path(y)
        boyut += sum(f.stat().st_size for f in (y.rglob("*") if y.is_dir() else [y]) if f.is_file())
    sure = time.time() - t0
    log(f"{model} indirildi: {boyut / 1e9:.1f} GB, {sure / 60:.1f} dk, {boyut / 1e6 / max(sure, 1):.0f} MB/sn")


# ---------------------------------------------------------------- sürücü
def alt_surec(argumanlar, zaman_asimi_dk):
    t0 = time.time()
    try:
        kod = subprocess.run([sys.executable, os.path.abspath(__file__)] + argumanlar,
                             timeout=zaman_asimi_dk * 60).returncode
    except subprocess.TimeoutExpired:
        kod = "zaman aşımı"
    return kod, round(time.time() - t0, 1)


def ortam_bilgisi():
    bilgi = {"python": sys.version.split()[0], "smoke": SMOKE}
    try:
        bilgi["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:
        bilgi["nvidia_smi"] = f"yok ({type(e).__name__})"
    import importlib.metadata as md
    for p in ("torch", "diffusers", "transformers", "accelerate", "imageio-ffmpeg"):
        try:
            bilgi[p] = md.version(p)
        except Exception:
            bilgi[p] = "yok"
    try:
        import psutil
        bilgi["ram_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
        bilgi["disk_bos_gb"] = round(psutil.disk_usage(str(KOK)).free / 1e9, 1)
    except Exception:
        pass
    return bilgi


def deneme_kaydi(cfg, kod, sure):
    j = CIKTI / f"{cfg['ad']}.json"
    if j.exists():
        return json.loads(j.read_text(encoding="utf-8"))
    neden = "süre sınırı aşıldı" if kod == "zaman aşımı" else (
        "süreç öldürüldü (büyük olasılıkla sistem belleği yetmedi)" if kod in (-9, 137) else f"süreç çöktü (kod {kod})")
    kayit = dict(cfg, durum="hata", neden=neden, sure_sn=sure)
    j.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    return kayit


KAYNAK_NEDENLERI = ("GPU belleği yetmedi", "süreç öldürüldü", "süre sınırı aşıldı")


denenen = set()          # denenen farklı ayarlar (yol + tür + boyut + kare)
bozuk_turler = set()     # bellek/süre dışı hatayla düşen model türleri (bütün merdivenlerde geçerli)


def butce_yetiyor(t_bas):
    """Bir deneme daha sığar mı? En az EN_AZ_AYAR farklı ayar denenmeden bütçe engel olmaz."""
    gecen = (time.time() - t_bas) / 60
    return len(denenen) < EN_AZ_AYAR or gecen + DENEME_ZAMAN_ASIMI_DK <= BUTCE_DK + 10


def merdiven_calistir(yol, model, merdiven, ek, t_bas, kayitlar):
    for i, basamak in enumerate(merdiven):
        tur, w, h, n = basamak if len(basamak) == 4 else (model, *basamak)
        if tur in bozuk_turler:
            continue
        ek_ad = f"_s{round(ek['sigma'] * 100)}" if "sigma" in ek else ""
        cfg = dict(ad=f"{yol}{ek_ad}_{tur}_{w}x{h}_{n}k", yol=yol, model=model, tur=tur, w=w, h=h, kare=n,
                   sira=i + 1, **ek)
        if not butce_yetiyor(t_bas):
            kayitlar.append(dict(cfg, durum="atlandı", neden=f"süre bütçesi ({BUTCE_DK:.0f} dk) doldu"))
            log(f"{cfg['ad']} atlandı: süre bütçesi doldu")
            break
        for eski in (f"{cfg['ad']}.json", f"{cfg['ad']}.mp4", f"{cfg['ad']}-serit.jpg"):
            (CIKTI / eski).unlink(missing_ok=True)
        gecen = (time.time() - t_bas) / 60
        sinir = DENEME_ZAMAN_ASIMI_DK if len(denenen) < EN_AZ_AYAR else \
            min(DENEME_ZAMAN_ASIMI_DK, max(10, BUTCE_DK + 15 - gecen))
        kod, sure = alt_surec(["--tek", json.dumps(cfg)], sinir)
        kayit = deneme_kaydi(cfg, kod, sure)
        denenen.add(cfg["ad"])
        kayitlar.append(kayit)
        if kayit["durum"] == "tamam":
            return True
        if not str(kayit.get("neden", "")).startswith(KAYNAK_NEDENLERI):
            bozuk_turler.add(tur)     # bellek/süre dışı hata: küçültmek çözmez, sıradaki model türüne geç
            log(f"{cfg['ad']} olmadı ({kayit.get('neden')}); '{tur}' türü bırakılıyor")
        else:
            log(f"{cfg['ad']} olmadı ({kayit.get('neden')}); bir alt ayara iniliyor")
    return False


def hazirla(model, kayitlar):
    """İndirme (süresiz) + metin gömmesi (en çok 2 deneme). Başarılıysa True."""
    kod, sure = alt_surec(["--indir", model], 120)
    if kod != 0:
        log(f"{model} indirme kodu {kod}; yine de metin aşaması deneniyor")
    for deneme in (1, 2):
        (KOK / f"gomme_{model}.pt").unlink(missing_ok=True)
        kod, sure = alt_surec(["--metin", model], 30)
        log(f"{model} metin gömmesi ({deneme}. deneme): kod {kod}, {sure} sn")
        if kod == 0 and (KOK / f"gomme_{model}.pt").exists():
            return True
    kayitlar.append(dict(ad=f"{model}_metin", durum="hata", neden=f"metin kodlayıcı çalışmadı (kod {kod})"))
    return False


def surucu():
    import shutil
    shutil.rmtree(CIKTI, ignore_errors=True)
    CIKTI.mkdir(parents=True, exist_ok=True)
    for eski in list(KOK.glob("gizli_*.pt")) + [KOK / "sdpa.json"]:
        eski.unlink(missing_ok=True)
    t_bas = time.time()
    bilgi = ortam_bilgisi()
    log("ortam:", json.dumps(bilgi, ensure_ascii=False))
    kayitlar, basari = [], {}
    try:
        _surucu_govde(t_bas, kayitlar, basari)
    finally:
        rapor = {"ortam": bilgi, "toplam_dk": round((time.time() - t_bas) / 60, 1), "denemeler": kayitlar,
                 "farkli_ayar_sayisi": len(denenen), "istem": ISTEM, "olumsuz_istem": OLUMSUZ,
                 "sdpa": json.loads((KOK / "sdpa.json").read_text(encoding="utf-8")) if (KOK / "sdpa.json").exists() else None,
                 "ltx": [LTX_DAMITIK, LTX_REPO], "wan_repolari": [WAN_T2V_REPO, WAN_VACE_REPO]}
        (CIKTI / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"bitti: {sum(1 for k in kayitlar if k.get('durum') == 'tamam')} başarılı deneme, "
            f"{len(denenen)} farklı ayar, {rapor['toplam_dk']} dk")


def _surucu_govde(t_bas, kayitlar, basari):
    sadece_wan = SMOKE and os.environ.get("ZIREK_SMOKE_SADECE_WAN") == "1"   # yalnız yerel sınama için
    if not sadece_wan and hazirla("ltx", kayitlar):
        basari["ltx_i2v"] = merdiven_calistir("ltx_i2v", "ltx", LTX_MERDIVEN, {}, t_bas, kayitlar)
        for sg in LTX_V2V_SIGMALAR:
            basari[f"ltx_v2v_{sg}"] = merdiven_calistir("ltx_v2v", "ltx", LTX_MERDIVEN, {"sigma": sg},
                                                        t_bas, kayitlar)

    if any(basari.values()):
        return
    if not butce_yetiyor(t_bas):
        kayitlar.append(dict(ad="wan", durum="atlandı", neden=f"süre bütçesi ({BUTCE_DK:.0f} dk) doldu"))
        return
    log("LTX hiçbir ayarda sonuç vermedi; Wan 2.1 1.3B deneniyor")
    if hazirla("wan", kayitlar):
        basari["wan_v2v"] = merdiven_calistir("wan_v2v", "wan", WAN_MERDIVEN, {"guc": 0.5}, t_bas, kayitlar)
        basari["wan_vace_i2v"] = merdiven_calistir("wan_vace_i2v", "wan", WAN_MERDIVEN, {"adim": 20}, t_bas,
                                                   kayitlar)


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")   # Hugging Face'e hiçbir anahtar gönderilmez
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")   # bellek parçalanmasına karşı
    nvrtc_hazirla()
    if "--tek" in sys.argv:
        tek(json.loads(sys.argv[sys.argv.index("--tek") + 1]))
    elif "--metin" in sys.argv:
        metin_gomme(sys.argv[sys.argv.index("--metin") + 1])
    elif "--indir" in sys.argv:
        indir(sys.argv[sys.argv.index("--indir") + 1])
    else:
        surucu()
