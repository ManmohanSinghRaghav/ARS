#!/usr/bin/env python3
"""
Test script to verify enhanced PDF generation from JSON.
"""

from app.pipeline.pro_pdf import generate_pro_pdf
import json

# Sample paper JSON
sample_paper = {
    "metadata": {
        "title": "Advanced Research in Machine Learning and Natural Language Processing",
        "author": "ARS Assistant (Autonomous Research Scientist)",
        "institution": "GLA Research Lab",
        "date": "May 2, 2026"
    },
    "sections": [
        {
            "id": "abstract",
            "type": "abstract",
            "title": "Abstract",
            "content": "This research explores the intersection of machine learning and natural language processing, presenting novel architectures for semantic understanding. Our approach demonstrates significant improvements in accuracy and efficiency compared to baseline methods. We validate our findings through comprehensive experiments and provide detailed analysis of results."
        },
        {
            "id": "introduction",
            "type": "content",
            "level": 1,
            "title": "1. Introduction",
            "content": "Natural language processing has undergone significant transformations over the past decade. **Modern approaches** utilize deep learning architectures that can capture complex semantic relationships in text data.\n\nKey contributions of this work:\n- Novel attention mechanism for long-range dependencies\n- Improved tokenization strategy for multilingual support\n- Comprehensive benchmark evaluation on standard datasets\n\nThe rest of this paper is organized as follows. Section 2 reviews related work, Section 3 presents our methodology, and Section 4 discusses experimental results."
        },
        {
            "id": "related_work",
            "type": "content",
            "level": 1,
            "title": "2. Related Work",
            "content": "Previous approaches to NLP can be categorized into three main paradigms:\n\n**Traditional Methods**: Rule-based systems and statistical approaches dominated NLP before the deep learning era.\n\n**Deep Learning Era**: The introduction of recurrent neural networks (RNNs) and later transformer architectures revolutionized the field.\n\n**Recent Advances**: Attention mechanisms, transfer learning, and large language models have achieved state-of-the-art results on numerous benchmarks."
        },
        {
            "id": "methodology",
            "type": "content",
            "level": 1,
            "title": "3. Methodology",
            "content": "Our approach consists of three main components:\n\n3.1 Preprocessing\nRaw text is tokenized using a custom tokenizer optimized for the target language.\n\n3.2 Architecture\nWe propose a hybrid architecture combining transformer and convolutional layers:\n\n```\nInput → Embedding → Transformer Blocks → Conv Layers → Attention → Output\n```\n\n3.3 Training\nModels are trained using Adam optimizer with a learning rate schedule and regularization techniques to prevent overfitting."
        },
        {
            "id": "results",
            "type": "content",
            "level": 1,
            "title": "4. Results",
            "content": "Our experimental evaluation includes benchmarks on three standard datasets. The following table summarizes the performance metrics:\n\n| Metric | Baseline | Our Method | Improvement |\n|--------|----------|-----------|-------------|\n| Accuracy | 0.8234 | 0.8756 | +5.22% |\n| F1-Score | 0.7891 | 0.8432 | +5.41% |\n| Speed (ms) | 145 | 89 | -38.6% |\n| Memory (MB) | 2048 | 1536 | -25.0% |\n\nThese results demonstrate significant improvements both in accuracy and efficiency."
        },
        {
            "id": "discussion",
            "type": "content",
            "level": 1,
            "title": "5. Discussion",
            "content": "The results validate our hypotheses about the effectiveness of hybrid architectures. The improvements in accuracy can be attributed to the combination of *global context capture* from transformers and *local pattern recognition* from convolutional layers.\n\nKey insights:\n1. The attention mechanism effectively captures long-range dependencies\n2. Hybrid architectures provide better efficiency-accuracy tradeoffs\n3. The approach generalizes well across different domains\n\nFuture work should explore scaling to larger datasets and investigating multi-task learning approaches."
        },
        {
            "id": "conclusion",
            "type": "content",
            "level": 1,
            "title": "6. Conclusion",
            "content": "We presented a novel hybrid architecture for natural language processing that achieves state-of-the-art results on multiple benchmarks. Our method combines the strengths of transformer and convolutional architectures while maintaining computational efficiency.\n\nThe comprehensive evaluation demonstrates the effectiveness of the proposed approach, with consistent improvements across multiple metrics. The work opens several avenues for future research, including extension to other NLP tasks and exploration of ensemble methods.\n\nIn conclusion, this research contributes to the advancing field of neural language understanding and provides practical improvements for real-world applications."
        }
    ]
}

# Generate PDF
try:
    print("[TEST] Generating enhanced PDF from JSON...")
    pdf_bytes = generate_pro_pdf(sample_paper)
    
    # Save to file
    output_path = "/Users/suryanshagarwal/ARS/backend/outputs/test_enhanced_pdf.pdf"
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✅ PDF generated successfully!")
    print(f"   File size: {len(pdf_bytes):,} bytes")
    print(f"   Saved to: {output_path}")
    print("\n✨ Enhanced PDF Features:")
    print("   ✓ Professional typography and spacing")
    print("   ✓ Tables with colored headers")
    print("   ✓ Bullet lists support")
    print("   ✓ Code block formatting")
    print("   ✓ Bold/Italic/Code text support")
    print("   ✓ Multi-level sections")
    print("   ✓ Abstract highlighting")
    print("   ✓ Automatic page breaks")
    
except Exception as e:
    print(f"❌ Error generating PDF: {e}")
    import traceback
    traceback.print_exc()
