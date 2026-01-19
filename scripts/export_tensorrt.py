#!/usr/bin/env python3
"""
TensorRT Model Export Script for Jetson Orin Nano

Exports YOLOv8 models to TensorRT engine format for optimized inference.
Run this once on the Jetson to generate the .engine file.

Usage:
    python3 export_tensorrt.py --model yolov8s.pt --output models/yolov8s.engine
    python3 export_tensorrt.py --model yolov8n.pt --output models/yolov8n.engine --fp16
"""

import argparse
import os
import sys
import time


def check_dependencies():
    """Verify required packages are installed"""
    missing = []
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            print(f"   CUDA: {torch.version.cuda}")
            print(f"   Device: {torch.cuda.get_device_name(0)}")
        else:
            print("   ⚠️  CUDA not available - export may be slow")
    except ImportError:
        missing.append("torch")
    
    try:
        import tensorrt as trt
        print(f"✅ TensorRT {trt.__version__}")
    except ImportError:
        missing.append("tensorrt")
    
    try:
        from ultralytics import YOLO
        print(f"✅ Ultralytics installed")
    except ImportError:
        missing.append("ultralytics")
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip3 install " + " ".join(missing))
        sys.exit(1)
    
    return True


def export_model(
    model_path: str,
    output_path: str,
    imgsz: int = 640,
    fp16: bool = True,
    batch_size: int = 1,
    workspace: int = 4,
    verbose: bool = False
):
    """
    Export YOLO model to TensorRT engine.
    
    Args:
        model_path: Path to PyTorch model (.pt)
        output_path: Output path for TensorRT engine (.engine)
        imgsz: Input image size
        fp16: Use FP16 precision (recommended for Jetson)
        batch_size: Batch size for inference
        workspace: TensorRT workspace size in GB
        verbose: Print detailed output
    """
    from ultralytics import YOLO
    
    print(f"\n{'='*60}")
    print("TensorRT Model Export")
    print(f"{'='*60}")
    print(f"Input:      {model_path}")
    print(f"Output:     {output_path}")
    print(f"Image Size: {imgsz}x{imgsz}")
    print(f"Precision:  {'FP16' if fp16 else 'FP32'}")
    print(f"Batch Size: {batch_size}")
    print(f"Workspace:  {workspace}GB")
    print(f"{'='*60}\n")
    
    # Check input exists
    if not os.path.exists(model_path):
        # Try downloading from ultralytics
        print(f"📥 Model not found locally, downloading {model_path}...")
    
    # Load model
    print("📦 Loading model...")
    model = YOLO(model_path)
    
    # Export to TensorRT
    print("🔧 Exporting to TensorRT (this may take 10-20 minutes)...")
    start_time = time.time()
    
    try:
        # Ultralytics handles the export
        exported = model.export(
            format='engine',
            imgsz=imgsz,
            half=fp16,
            batch=batch_size,
            workspace=workspace,
            verbose=verbose,
            device=0  # Use GPU
        )
        
        export_time = time.time() - start_time
        
        # The export creates a file with .engine extension
        # Move it to the desired output path if different
        default_output = model_path.replace('.pt', '.engine')
        if os.path.exists(default_output) and default_output != output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            os.rename(default_output, output_path)
        
        print(f"\n{'='*60}")
        print(f"✅ Export completed in {export_time:.1f} seconds")
        print(f"📁 Engine saved to: {output_path}")
        
        # Print file size
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"📊 File size: {size_mb:.1f} MB")
        
        print(f"{'='*60}\n")
        
        return output_path
        
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you have enough disk space (need ~2GB free)")
        print("2. Try reducing workspace: --workspace 2")
        print("3. Try FP32 if FP16 fails: remove --fp16")
        print("4. Check CUDA/TensorRT installation")
        sys.exit(1)


def benchmark_engine(engine_path: str, iterations: int = 100):
    """
    Benchmark the exported TensorRT engine.
    """
    import numpy as np
    
    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit
    except ImportError:
        print("⚠️  Cannot benchmark without TensorRT/PyCUDA")
        return
    
    print(f"\n{'='*60}")
    print("Benchmarking TensorRT Engine")
    print(f"{'='*60}")
    
    # Load engine
    logger = trt.Logger(trt.Logger.WARNING)
    with open(engine_path, "rb") as f:
        runtime = trt.Runtime(logger)
        engine = runtime.deserialize_cuda_engine(f.read())
    
    context = engine.create_execution_context()
    
    # Get input/output shapes
    input_shape = engine.get_binding_shape(0)
    print(f"Input shape: {input_shape}")
    
    # Create dummy input
    input_data = np.random.randn(*input_shape).astype(np.float32)
    
    # Allocate buffers
    d_input = cuda.mem_alloc(input_data.nbytes)
    output_shape = engine.get_binding_shape(1)
    output_size = trt.volume(output_shape)
    d_output = cuda.mem_alloc(output_size * np.dtype(np.float32).itemsize)
    h_output = cuda.pagelocked_empty(output_size, np.float32)
    
    stream = cuda.Stream()
    
    # Warmup
    print("Warming up...")
    for _ in range(10):
        cuda.memcpy_htod_async(d_input, input_data, stream)
        context.execute_async_v2([int(d_input), int(d_output)], stream.handle)
        cuda.memcpy_dtoh_async(h_output, d_output, stream)
        stream.synchronize()
    
    # Benchmark
    print(f"Running {iterations} iterations...")
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        cuda.memcpy_htod_async(d_input, input_data, stream)
        context.execute_async_v2([int(d_input), int(d_output)], stream.handle)
        cuda.memcpy_dtoh_async(h_output, d_output, stream)
        stream.synchronize()
        times.append((time.perf_counter() - start) * 1000)
    
    # Results
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    fps = 1000 / avg_time
    
    print(f"\n{'='*60}")
    print("Results:")
    print(f"  Average: {avg_time:.2f} ms")
    print(f"  Min:     {min_time:.2f} ms")
    print(f"  Max:     {max_time:.2f} ms")
    print(f"  FPS:     {fps:.1f}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 to TensorRT for Jetson",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Export YOLOv8s with FP16 (recommended)
    python3 export_tensorrt.py --model yolov8s.pt --output models/yolov8s.engine
    
    # Export smaller model for faster inference
    python3 export_tensorrt.py --model yolov8n.pt --output models/yolov8n.engine
    
    # Export with FP32 (if FP16 causes issues)
    python3 export_tensorrt.py --model yolov8s.pt --output models/yolov8s.engine --no-fp16
    
    # Benchmark after export
    python3 export_tensorrt.py --model yolov8s.pt --output models/yolov8s.engine --benchmark
        """
    )
    
    parser.add_argument('--model', type=str, default='yolov8s.pt',
                        help='Input PyTorch model path (default: yolov8s.pt)')
    parser.add_argument('--output', type=str, default='models/yolov8s.engine',
                        help='Output TensorRT engine path')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='Input image size (default: 640)')
    parser.add_argument('--fp16', action='store_true', default=True,
                        help='Use FP16 precision (default: True)')
    parser.add_argument('--no-fp16', action='store_false', dest='fp16',
                        help='Use FP32 precision')
    parser.add_argument('--batch', type=int, default=1,
                        help='Batch size (default: 1)')
    parser.add_argument('--workspace', type=int, default=4,
                        help='TensorRT workspace size in GB (default: 4)')
    parser.add_argument('--benchmark', action='store_true',
                        help='Run benchmark after export')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Create output directory
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    
    # Export model
    engine_path = export_model(
        model_path=args.model,
        output_path=args.output,
        imgsz=args.imgsz,
        fp16=args.fp16,
        batch_size=args.batch,
        workspace=args.workspace,
        verbose=args.verbose
    )
    
    # Benchmark if requested
    if args.benchmark and os.path.exists(engine_path):
        benchmark_engine(engine_path)


if __name__ == "__main__":
    main()
