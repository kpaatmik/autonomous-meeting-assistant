from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch


class QuestionDetector:
    """
    Question detector using FLAN-T5 Base
    """

    def __init__(self):

        model_name = "google/flan-t5-base"

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    def detect(self, text: str):

        if not text or len(text.strip()) < 3:
            return {"is_question": False}

        text = text.strip()

        # Fast rule check
        if text.endswith("?"):
            return {
                "is_question": True,
                "confidence": 0.99,
                "type": "explicit"
            }

        prompt = f"""
Is the following sentence a question?

Sentence: "{text}"

Answer YES or NO only.
"""

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=3,
                do_sample=False
            )

        answer = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        ).lower().strip()

        if answer.startswith("yes"):
            return {
                "is_question": True,
                "confidence": 0.85,
                "type": "implicit"
            }

        return {"is_question": False}


if __name__ == "__main__":

    detector = QuestionDetector()

    test_sentences = [
        "Did you send the report",
        "Please send the report tomorrow",
        "Can you explain this slide?",
        "The meeting will start at 3 PM",
        "Why is the server down"
    ]

    print("\nRunning Question Detection Test\n")

    for sentence in test_sentences:
        result = detector.detect(sentence)

        print("Input :", sentence)
        print("Output:", result)
        print("-" * 40)