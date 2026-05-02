#!/usr/bin/env python3
"""Test PDF generation locally with sample data."""

import sys
import json
sys.path.insert(0, '/Users/suryanshagarwal/ARS/backend')

from app.pipeline.pro_pdf import generate_pro_pdf

# Sample paper JSON matching the expected structure
sample_paper = {
    "metadata": {
        "title": "Blind Zero-Watermarking for Deepfakes Detection via CNNs",
        "author": "ARS Research Assistant",
        "institution": "Research Institute",
        "date": "May 2, 2026"
    },
    "sections": [
        {
            "type": "abstract",
            "title": "Abstract",
            "level": 1,
            "content": "This research presents a novel approach for detecting deepfakes using blind zero-watermarking techniques with convolutional neural networks. We explore advanced detection methods that do not require watermark information..."
        },
        {
            "type": "content",
            "title": "Introduction",
            "level": 1,
            "content": "The rapid advancement of deep learning has enabled the creation of highly realistic synthetic media. This section introduces the problem of deepfake detection and the motivation for our research.\n\nKey challenges include:\n- Detection accuracy in real-world scenarios\n- Computational efficiency\n- Robustness against various attack vectors"
        },
        {
            "type": "content",
            "title": "Methodology",
            "level": 1,
            "content": "We propose a multi-stage approach combining:\n\n1. Feature extraction using ResNet-50\n2. Zero-watermarking embedding\n3. Classification using binary CNN\n\nThe system achieves 94.5% accuracy on the benchmark dataset."
        },
        {
            "type": "content",
            "title": "Results",
            "level": 1,
            "content": "| Method | Accuracy | F1-Score |\n| --- | --- | --- |\n| Baseline CNN | 87.2% | 0.86 |\n| Zero-Watermarking | 92.1% | 0.91 |\n| Proposed (Blind) | 94.5% | 0.93 |"
        },
        {
            "type": "content",
            "title": "Discussion",
            "level": 1,
            "content": "The proposed method significantly outperforms existing approaches. Key advantages:\n\n- **Robustness**: Works without original watermark\n- **Efficiency**: Fast inference time\n- **Scalability**: Suitable for real-time detection"
        },
        {
            "type": "content",
            "title": "Conclusion",
            "level": 1,
            "content": "Our blind zero-watermarking approach provides a practical solution for deepfake detection. Future work will focus on extending to video content and exploring adversarial robustness."
        }
    ]
}

print("Testing PDF generation with sample data...")
print(f"Sample JSON keys: {sample_paper.keys()}")
print(f"Number of sections: {len(sample_paper.get('sections', []))}")

try:
    print("\nGenerating PDF...")
    pdf_bytes = generate_pro_pdf(sample_paper)
    
    # Save to file
    output_path = '/Users/suryanshagarwal/ARS/test_output.pdf'
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    
    print(f"✅ PDF generated successfully!")
    print(f"   File size: {len(pdf_bytes)} bytes")
    print(f"   Saved to: {output_path}")
    
except Exception as e:
    print(f"❌ Error generating PDF: {e}")
    import traceback
    traceback.print_exc()
