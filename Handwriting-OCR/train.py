#!/usr/bin/env python3
"""
Training Data Preparation Script for PaddleOCR

This script processes approved handwriting samples and prepares them for training
a custom PaddleOCR model. It handles data validation, image preprocessing,
and generates the required training files.
"""

import json
import logging
import sys
from pathlib import Path
from shutil import copyfile
from typing import Dict, List, Tuple, Optional
import hashlib
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('train_preparation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TrainingDataPreparer:
    """Handles preparation of training data for PaddleOCR fine-tuning."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the training data preparer.
        
        Args:
            base_dir: Base directory path. Defaults to script directory.
        """
        self.base_dir = base_dir or Path(__file__).parent.resolve()
        self.data_dir = self.base_dir / "data"
        self.approved_dir = self.data_dir / "approved"
        self.output_dir = self.base_dir / "train_data"
        self.labels_file = self.data_dir / "labels.json"
        
        # Create necessary directories
        self._setup_directories()
        
    def _setup_directories(self) -> None:
        """Create required directories if they don't exist."""
        directories = [self.data_dir, self.approved_dir, self.output_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def _load_labels(self) -> Dict:
        """Load labels from JSON file with error handling.
        
        Returns:
            Dictionary containing label data.
            
        Raises:
            FileNotFoundError: If labels file doesn't exist.
            json.JSONDecodeError: If labels file is corrupted.
        """
        if not self.labels_file.exists():
            raise FileNotFoundError(f"Labels file not found: {self.labels_file}")
        
        try:
            with open(self.labels_file, "r", encoding="utf-8") as f:
                labels = json.load(f)
            logger.info(f"Loaded {len(labels)} labels from {self.labels_file}")
            return labels
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse labels file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading labels: {e}")
            raise
    
    def _validate_image_file(self, file_path: Path) -> bool:
        """Validate that an image file exists and is readable.
        
        Args:
            file_path: Path to the image file.
            
        Returns:
            True if file is valid, False otherwise.
        """
        if not file_path.exists():
            logger.warning(f"Image file not found: {file_path}")
            return False
        
        if file_path.stat().st_size == 0:
            logger.warning(f"Image file is empty: {file_path}")
            return False
        
        # Check if file has valid image extension
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        if file_path.suffix.lower() not in valid_extensions:
            logger.warning(f"Invalid image extension: {file_path}")
            return False
        
        return True
    
    def _sanitize_text(self, text: str) -> str:
        """Clean and sanitize text for training.
        
        Args:
            text: Raw text to sanitize.
            
        Returns:
            Cleaned text suitable for training.
        """
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        text = " ".join(text.split())
        
        # Remove or replace problematic characters
        text = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
        
        # Ensure text is not too long (PaddleOCR limitation)
        max_length = 1000
        if len(text) > max_length:
            logger.warning(f"Text truncated from {len(text)} to {max_length} characters")
            text = text[:max_length]
        
        return text.strip()
    
    def _get_best_text(self, entry: Dict) -> str:
        """Get the best available text for training from an entry.
        
        Args:
            entry: Label entry dictionary.
            
        Returns:
            Best available text for training.
        """
        # Priority: corrected_text > provided_text > predicted_text
        text_sources = [
            entry.get("corrected_text", ""),
            entry.get("provided_text", ""),
            entry.get("predicted_text", "")
        ]
        
        for text in text_sources:
            if text and text.strip():
                return self._sanitize_text(text)
        
        return ""
    
    def _copy_with_verification(self, src: Path, dst: Path) -> bool:
        """Copy file with verification.
        
        Args:
            src: Source file path.
            dst: Destination file path.
            
        Returns:
            True if copy was successful, False otherwise.
        """
        try:
            # Get source file hash for verification
            with open(src, 'rb') as f:
                src_hash = hashlib.md5(f.read()).hexdigest()
            
            copyfile(src, dst)
            
            # Verify copy
            with open(dst, 'rb') as f:
                dst_hash = hashlib.md5(f.read()).hexdigest()
            
            if src_hash != dst_hash:
                logger.error(f"File copy verification failed: {src} -> {dst}")
                dst.unlink(missing_ok=True)
                return False
            
            logger.debug(f"Successfully copied: {src} -> {dst}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file {src} -> {dst}: {e}")
            return False
    
    def prepare_training_data(self) -> Tuple[int, int]:
        """Prepare training data from approved samples.
        
        Returns:
            Tuple of (successful_samples, total_approved_samples).
        """
        logger.info("Starting training data preparation...")
        
        try:
            labels = self._load_labels()
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")
            return 0, 0
        
        train_list = []
        successful_copies = 0
        total_approved = 0
        skipped_samples = []
        
        for uid, entry in labels.items():
            if entry.get("status") != "approved":
                continue
            
            total_approved += 1
            img_name = entry.get("file")
            
            if not img_name:
                logger.warning(f"No filename for entry {uid}")
                skipped_samples.append((uid, "No filename"))
                continue
            
            # Get the best available text
            text = self._get_best_text(entry)
            if not text:
                logger.warning(f"No valid text for entry {uid}")
                skipped_samples.append((uid, "No valid text"))
                continue
            
            # Validate source file
            src_path = self.approved_dir / img_name
            if not self._validate_image_file(src_path):
                skipped_samples.append((uid, f"Invalid image file: {src_path}"))
                continue
            
            # Copy to training directory
            dst_path = self.output_dir / img_name
            if not self._copy_with_verification(src_path, dst_path):
                skipped_samples.append((uid, "File copy failed"))
                continue
            
            # Add to training list
            train_list.append(f"{img_name}\t{text}")
            successful_copies += 1
            logger.debug(f"Prepared sample {uid}: {img_name}")
        
        # Write training list file
        train_file = self.output_dir / "train.txt"
        try:
            with open(train_file, "w", encoding="utf-8") as f:
                f.write("\n".join(train_list))
            logger.info(f"Created training file: {train_file}")
        except Exception as e:
            logger.error(f"Failed to write training file: {e}")
            return 0, total_approved
        
        # Write validation list (using same data for now)
        val_file = self.output_dir / "val.txt"
        try:
            with open(val_file, "w", encoding="utf-8") as f:
                f.write("\n".join(train_list))
            logger.info(f"Created validation file: {val_file}")
        except Exception as e:
            logger.warning(f"Failed to write validation file: {e}")
        
        # Generate summary report
        self._generate_report(successful_copies, total_approved, skipped_samples)
        
        return successful_copies, total_approved
    
    def _generate_report(self, successful: int, total: int, skipped: List[Tuple[str, str]]) -> None:
        """Generate a detailed preparation report.
        
        Args:
            successful: Number of successfully processed samples.
            total: Total number of approved samples.
            skipped: List of skipped samples with reasons.
        """
        report_file = self.output_dir / "preparation_report.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_content = f"""Training Data Preparation Report
Generated: {timestamp}

Summary:
- Total approved samples: {total}
- Successfully processed: {successful}
- Skipped samples: {len(skipped)}
- Success rate: {(successful/total*100) if total > 0 else 0:.1f}%

Output Directory: {self.output_dir}
Files Generated:
- train.txt: {successful} samples
- val.txt: {successful} samples
- preparation_report.txt: This report

"""
        
        if skipped:
            report_content += "Skipped Samples:\n"
            for uid, reason in skipped:
                report_content += f"- {uid}: {reason}\n"
        
        report_content += f"""
Next Steps:
1. Review the generated train.txt and val.txt files
2. Run monitor.py to check training readiness
3. Follow PaddleOCR training documentation
4. Use the prepared data for fine-tuning your model

Training Command Example:
python -m paddle.distributed.launch --gpus '0' tools/train.py -c configs/rec/rec_icdar15_train.yml

Monitor training progress:
python monitor.py
"""
        
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"Generated preparation report: {report_file}")
        except Exception as e:
            logger.error(f"Failed to write report: {e}")


def main():
    """Main function to run the training data preparation."""
    try:
        preparer = TrainingDataPreparer()
        successful, total = preparer.prepare_training_data()
        
        if successful == 0:
            logger.error("No training samples were prepared successfully!")
            sys.exit(1)
        
        logger.info(f"Training data preparation completed!")
        logger.info(f"Successfully prepared {successful}/{total} approved samples")
        logger.info(f"Training data available in: {preparer.output_dir}")
        
        if successful < total:
            logger.warning(f"Some samples were skipped. Check the preparation report for details.")
        
    except KeyboardInterrupt:
        logger.info("Training data preparation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during preparation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()