#!/usr/bin/env python3
"""
OCR Training Monitor

Monitors the OCR training process and provides insights into model performance.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OCRMonitor:
    """Monitors OCR training data and model performance."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the OCR monitor.
        
        Args:
            base_dir: Base directory path. Defaults to script directory.
        """
        self.base_dir = base_dir or Path(__file__).parent.resolve()
        self.data_dir = self.base_dir / "data"
        self.labels_file = self.data_dir / "labels.json"
        self.train_data_dir = self.base_dir / "train_data"
        self.reports_dir = self.base_dir / "reports"
        
        # Create reports directory
        self.reports_dir.mkdir(exist_ok=True)
    
    def load_labels(self) -> Dict:
        """Load labels from JSON file."""
        if not self.labels_file.exists():
            logger.warning("Labels file not found")
            return {}
        
        try:
            with open(self.labels_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")
            return {}
    
    def analyze_dataset(self) -> Dict:
        """Analyze the current dataset."""
        labels = self.load_labels()
        
        if not labels:
            return {"error": "No data available"}
        
        analysis = {
            "total_samples": len(labels),
            "status_breakdown": defaultdict(int),
            "text_length_stats": [],
            "character_frequency": Counter(),
            "word_frequency": Counter(),
            "quality_metrics": {
                "has_predicted_text": 0,
                "has_provided_text": 0,
                "has_corrected_text": 0,
                "prediction_accuracy": []
            },
            "file_stats": {
                "total_size": 0,
                "avg_size": 0,
                "size_distribution": []
            }
        }
        
        for uid, entry in labels.items():
            # Status breakdown
            status = entry.get("status", "unknown")
            analysis["status_breakdown"][status] += 1
            
            # Text analysis
            texts = [
                entry.get("predicted_text", ""),
                entry.get("provided_text", ""),
                entry.get("corrected_text", "")
            ]
            
            for text in texts:
                if text:
                    analysis["text_length_stats"].append(len(text))
                    # Character frequency
                    for char in text.lower():
                        if char.isalnum() or char.isspace():
                            analysis["character_frequency"][char] += 1
                    # Word frequency
                    words = text.lower().split()
                    for word in words:
                        if word.isalnum():
                            analysis["word_frequency"][word] += 1
            
            # Quality metrics
            if entry.get("predicted_text"):
                analysis["quality_metrics"]["has_predicted_text"] += 1
            if entry.get("provided_text"):
                analysis["quality_metrics"]["has_provided_text"] += 1
            if entry.get("corrected_text"):
                analysis["quality_metrics"]["has_corrected_text"] += 1
            
            # Compare prediction vs provided text for accuracy
            pred = entry.get("predicted_text", "").lower().strip()
            prov = entry.get("provided_text", "").lower().strip()
            if pred and prov:
                # Simple accuracy: exact match
                accuracy = 1.0 if pred == prov else 0.0
                analysis["quality_metrics"]["prediction_accuracy"].append(accuracy)
            
            # File stats
            file_size = entry.get("file_size", 0)
            analysis["file_stats"]["total_size"] += file_size
            analysis["file_stats"]["size_distribution"].append(file_size)
        
        # Calculate averages
        if analysis["text_length_stats"]:
            analysis["avg_text_length"] = np.mean(analysis["text_length_stats"])
            analysis["text_length_std"] = np.std(analysis["text_length_stats"])
        
        if analysis["file_stats"]["size_distribution"]:
            analysis["file_stats"]["avg_size"] = np.mean(analysis["file_stats"]["size_distribution"])
        
        if analysis["quality_metrics"]["prediction_accuracy"]:
            analysis["quality_metrics"]["avg_accuracy"] = np.mean(analysis["quality_metrics"]["prediction_accuracy"])
        
        return analysis
    
    def generate_training_readiness_report(self) -> Dict:
        """Generate a report on training readiness."""
        labels = self.load_labels()
        
        if not labels:
            return {"ready": False, "reason": "No data available"}
        
        approved_samples = [
            entry for entry in labels.values() 
            if entry.get("status") == "approved"
        ]
        
        report = {
            "ready": False,
            "total_samples": len(labels),
            "approved_samples": len(approved_samples),
            "minimum_required": 100,  # Minimum samples for meaningful training
            "recommendations": [],
            "quality_issues": [],
            "training_data_exists": (self.train_data_dir / "train.txt").exists()
        }
        
        # Check minimum samples
        if len(approved_samples) < report["minimum_required"]:
            report["recommendations"].append(
                f"Need at least {report['minimum_required']} approved samples. "
                f"Currently have {len(approved_samples)}."
            )
        
        # Check for corrected text
        samples_with_corrections = [
            s for s in approved_samples 
            if s.get("corrected_text", "").strip()
        ]
        
        if len(samples_with_corrections) < len(approved_samples) * 0.8:
            report["quality_issues"].append(
                "Less than 80% of approved samples have corrected text"
            )
        
        # Check text diversity
        all_texts = [s.get("corrected_text", "") for s in approved_samples]
        unique_texts = set(text.lower().strip() for text in all_texts if text.strip())
        
        if len(unique_texts) < len(approved_samples) * 0.7:
            report["quality_issues"].append(
                "Low text diversity - many duplicate texts detected"
            )
        
        # Overall readiness
        report["ready"] = (
            len(approved_samples) >= report["minimum_required"] and
            len(report["quality_issues"]) == 0
        )
        
        return report
    
    def create_visualizations(self) -> None:
        """Create visualization charts for the dataset."""
        analysis = self.analyze_dataset()
        
        if "error" in analysis:
            logger.error("Cannot create visualizations: " + analysis["error"])
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('OCR Training Dataset Analysis', fontsize=16, fontweight='bold')
        
        # 1. Status breakdown pie chart
        status_data = dict(analysis["status_breakdown"])
        if status_data:
            axes[0, 0].pie(status_data.values(), labels=status_data.keys(), autopct='%1.1f%%')
            axes[0, 0].set_title('Sample Status Distribution')
        
        # 2. Text length distribution
        if analysis["text_length_stats"]:
            axes[0, 1].hist(analysis["text_length_stats"], bins=20, alpha=0.7, color='skyblue')
            axes[0, 1].set_title('Text Length Distribution')
            axes[0, 1].set_xlabel('Text Length (characters)')
            axes[0, 1].set_ylabel('Frequency')
        
        # 3. Top characters
        if analysis["character_frequency"]:
            top_chars = analysis["character_frequency"].most_common(15)
            chars, counts = zip(*top_chars)
            axes[1, 0].bar(chars, counts, color='lightcoral')
            axes[1, 0].set_title('Most Common Characters')
            axes[1, 0].set_xlabel('Characters')
            axes[1, 0].set_ylabel('Frequency')
        
        # 4. File size distribution
        if analysis["file_stats"]["size_distribution"]:
            sizes_mb = [size / (1024 * 1024) for size in analysis["file_stats"]["size_distribution"]]
            axes[1, 1].hist(sizes_mb, bins=20, alpha=0.7, color='lightgreen')
            axes[1, 1].set_title('File Size Distribution')
            axes[1, 1].set_xlabel('File Size (MB)')
            axes[1, 1].set_ylabel('Frequency')
        
        plt.tight_layout()
        
        # Save the plot
        plot_file = self.reports_dir / f"dataset_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualization saved to: {plot_file}")
    
    def generate_comprehensive_report(self) -> str:
        """Generate a comprehensive monitoring report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        analysis = self.analyze_dataset()
        readiness = self.generate_training_readiness_report()
        
        report_content = f"""
# OCR Training Dataset Monitoring Report
Generated: {timestamp}

## Dataset Overview
- Total Samples: {analysis.get('total_samples', 0)}
- Average Text Length: {analysis.get('avg_text_length', 0):.1f} characters
- Total Dataset Size: {analysis.get('file_stats', {}).get('total_size', 0) / (1024*1024):.1f} MB

## Status Breakdown
"""
        
        for status, count in analysis.get("status_breakdown", {}).items():
            percentage = (count / analysis.get('total_samples', 1)) * 100
            report_content += f"- {status.title()}: {count} ({percentage:.1f}%)\n"
        
        report_content += f"""
## Quality Metrics
- Samples with OCR predictions: {analysis.get('quality_metrics', {}).get('has_predicted_text', 0)}
- Samples with user-provided text: {analysis.get('quality_metrics', {}).get('has_provided_text', 0)}
- Samples with corrected text: {analysis.get('quality_metrics', {}).get('has_corrected_text', 0)}
"""
        
        if analysis.get('quality_metrics', {}).get('prediction_accuracy'):
            avg_acc = analysis['quality_metrics'].get('avg_accuracy', 0)
            report_content += f"- Average OCR accuracy: {avg_acc:.1%}\n"
        
        report_content += f"""
## Training Readiness
- Ready for training: {'✅ Yes' if readiness['ready'] else '❌ No'}
- Approved samples: {readiness['approved_samples']} / {readiness['minimum_required']} minimum
- Training data prepared: {'✅ Yes' if readiness['training_data_exists'] else '❌ No'}
"""
        
        if readiness['recommendations']:
            report_content += "\n### Recommendations\n"
            for rec in readiness['recommendations']:
                report_content += f"- {rec}\n"
        
        if readiness['quality_issues']:
            report_content += "\n### Quality Issues\n"
            for issue in readiness['quality_issues']:
                report_content += f"- ⚠️ {issue}\n"
        
        # Top words and characters
        if analysis.get('word_frequency'):
            top_words = analysis['word_frequency'].most_common(10)
            report_content += "\n### Most Common Words\n"
            for word, count in top_words:
                report_content += f"- '{word}': {count} times\n"
        
        report_content += f"""
## Next Steps
1. {'✅' if readiness['approved_samples'] >= 100 else '⏳'} Collect at least 100 approved samples
2. {'✅' if readiness['training_data_exists'] else '⏳'} Run train.py to prepare training data
3. {'⏳'} Train custom PaddleOCR model with prepared data
4. {'⏳'} Evaluate model performance and iterate

## Training Commands
```bash
# Prepare training data
python train.py

# Train PaddleOCR model (example)
python -m paddle.distributed.launch --gpus '0' tools/train.py -c configs/rec/rec_icdar15_train.yml
```
"""
        
        # Save report
        report_file = self.reports_dir / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"Comprehensive report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        return report_content
    
    def monitor_training_progress(self, training_log_file: Optional[Path] = None) -> Dict:
        """Monitor training progress from log files."""
        if not training_log_file or not training_log_file.exists():
            return {"error": "Training log file not found"}
        
        progress = {
            "epochs_completed": 0,
            "current_loss": None,
            "best_accuracy": None,
            "training_time": None,
            "status": "unknown"
        }
        
        try:
            with open(training_log_file, "r") as f:
                lines = f.readlines()
            
            # Parse training logs (this would need to be adapted based on actual log format)
            for line in lines:
                if "epoch" in line.lower():
                    # Extract epoch information
                    pass
                if "loss" in line.lower():
                    # Extract loss information
                    pass
                if "accuracy" in line.lower():
                    # Extract accuracy information
                    pass
            
        except Exception as e:
            logger.error(f"Failed to parse training log: {e}")
            return {"error": str(e)}
        
        return progress


def main():
    """Main function to run the monitoring."""
    try:
        monitor = OCRMonitor()
        
        logger.info("Starting OCR training monitoring...")
        
        # Generate comprehensive report
        report = monitor.generate_comprehensive_report()
        print("\n" + "="*60)
        print("MONITORING REPORT")
        print("="*60)
        print(report)
        
        # Create visualizations
        try:
            monitor.create_visualizations()
        except ImportError:
            logger.warning("Matplotlib not available. Install with: pip install matplotlib")
        except Exception as e:
            logger.error(f"Failed to create visualizations: {e}")
        
        # Check training readiness
        readiness = monitor.generate_training_readiness_report()
        if readiness['ready']:
            logger.info("✅ Dataset is ready for training!")
        else:
            logger.warning("⚠️ Dataset needs more work before training")
        
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during monitoring: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()