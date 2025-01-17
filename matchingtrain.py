import logging
import torch
from datasets import load_from_disk, concatenate_datasets
from transformers import (
    AutoConfig,
    AutoTokenizer,
    default_data_collator,
    TrainingArguments,
)
from SimCSE.models import RobertaForCL
from SimCSE.arguments import ModelArguments, DataTrainingArguments, OurTrainingArguments
from SimCSE.data_collator import SimCseDataCollatorWithPadding
from SimCSE.trainers import CLTrainer
from metric import compute_metrics

logger = logging.getLogger(__name__)

# 변수 설정
base = "kazma1/"  #kazma1/unsupervise_bert_base,kazma1/unsuperivse_roberta_large,kazma1/unsupervise_roberta_base,kazma1/unsupervise_roberta_small
name = "simcse-robertsmall-matching"
model_name = f"{base}{name}"
train_batch_size = 16
step_num = 1000
OMP_NUM_THREADS = 8
output_dir = "output/simcse-robertsmall-bootstrap"

def main():
    # 데이터 인자와 훈련 인자를 초기화합니다.
    data_args = DataTrainingArguments(
        train_file=None,
        dev_file=None,
        test_file=None,
        pad_to_max_length=False,
    )



    # GPU 사용 여부 확인
    
    device = torch.device( "cpu")

    print(f"Using device: {device}")

  

    training_args = OurTrainingArguments(
        output_dir=output_dir,
        learning_rate=0.00005,
        do_train=True,
        save_total_limit=2,
        do_eval= True,
        deepspeed=False,
        logging_steps=step_num,
        save_steps=step_num,
        evaluation_strategy="steps",
        eval_steps=step_num,
        load_best_model_at_end=True,
        label_names=["labels"],
        num_train_epochs=5
    )

    config = AutoConfig.from_pretrained(model_name)
    model = RobertaForCL.from_pretrained(
        model_name,
        from_tf=bool(".ckpt" in model_name),
        config=config,
        cache_dir=None,
        revision=None,
        use_auth_token=None,
        model_args=ModelArguments(do_mlm=True),
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.resize_token_embeddings(len(tokenizer))

    train_dataset = load_from_disk(("data/sts/bootstrap/dev"))

    data_collator = (
        default_data_collator
        if data_args.pad_to_max_length
        else SimCseDataCollatorWithPadding(
            tokenizer=tokenizer, data_args=data_args, model_args=ModelArguments(do_mlm=False)
        )
    )

    # 평가 데이터셋 로드
    eval_dataset = load_from_disk("data/sts/eval/dev")

    
  # Shape of input data 출력
    for key, value in train_dataset[0].items():
        if isinstance(value, list):
            for i, item in enumerate(value):
                print(f"Key: {key}[{i}], Shape: {item.shape if hasattr(item, 'shape') else 'Not available'}")
        else:
            print(f"Key: {key}, Shape: {value.shape if hasattr(value, 'shape') else 'Not available'}")




    trainer = CLTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        compute_metrics=lambda eval_pred: compute_metrics(eval_pred, model=model),
    )

    trainer.train()
    # 평가 수행 및 결과 출력
    eval_results = trainer.evaluate(eval_dataset)
    logger.info(f"Final Evaluation Results: {eval_results}")
 
    model.save_pretrained(f"{output_dir}/best_model")
    tokenizer.save_pretrained(f"{output_dir}/best_model")

if __name__ == "__main__":
    main()
