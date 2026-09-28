use fframes::{EncoderOptions, RenderOptions, cli};
use std::process::ExitCode;
use zirek_duz2d::{ZirekMedia, ZirekVideo};

// Same encoder settings as the HyperFrames duz2d render: libx264, CRF 16, preset medium, yuv420p.
const CODEC_PARAMS: &[(&str, &str)] = &[("crf", "16"), ("preset", "medium")];

fn main() -> ExitCode {
    let media = ZirekMedia::new().expect("media");
    let video = ZirekVideo::new();
    let options = RenderOptions {
        media: Some(&media),
        video_encoder_options: EncoderOptions {
            preferred_encoder: Some("libx264"),
            codec_params: Some(CODEC_PARAMS),
            ..Default::default()
        },
        ..Default::default()
    };

    #[cfg(feature = "skia")]
    {
        use fframes_skia_renderer::{
            SkiaFFramesRenderer, SkiaPipelineConcurrencyPolicy, SkiaPipelineConfig,
            vulkan::SkiaVulkanCtx,
        };
        let gpu = SkiaVulkanCtx::new(zirek_duz2d::WIDTH, zirek_duz2d::HEIGHT).expect("Vulkan context");
        return cli::new(&video, options)
            .backend(
                SkiaFFramesRenderer::new_vulkan(
                    &gpu,
                    SkiaPipelineConfig {
                        concurrency_policy: SkiaPipelineConcurrencyPolicy::MaxPerformance,
                        ..Default::default()
                    },
                )
                .expect("skia renderer"),
            )
            .run();
    }

    #[cfg(not(feature = "skia"))]
    cli::new(&video, options).run()
}
