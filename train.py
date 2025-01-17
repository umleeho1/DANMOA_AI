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
base = "klue/"
name = "roberta-large"
model_name = f"{base}{name}"
train_batch_size = 8
step_num = 100
OMP_NUM_THREADS = 8
output_dir = "output/simcse"

def main():
    # 데이터 인자와 훈련 인자를 초기화합니다.
    data_args = DataTrainingArguments(
        train_file=None,
        dev_file=None,
        test_file=None,
        pad_to_max_length=False,
    )



    # GPU 사용 여부 확인
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    training_args = OurTrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=train_batch_size,
        #per_device_eval_batch_size=train_batch_size,
        learning_rate=7e-5,
        do_train=True,
        #save_total_limit=1,
        do_eval= False,
        deepspeed=False, 
        logging_steps=step_num,
        #save_steps=step_num,
        evaluation_strategy="no",#eval없을시 no
        #eval_steps=step_num,  #eval없을시 주석처리
        load_best_model_at_end=False, #eval없을시 false
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
        model_args=ModelArguments(do_mlm=False),
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.resize_token_embeddings(len(tokenizer))

    # 두 데이터셋을 합칩니다.
    dataset1 = load_from_disk("data/linkareer/train")
    dataset2 = load_from_disk("data/wanted/train")
    combined_dataset = concatenate_datasets([dataset1, dataset2])

    data_collator = (
        default_data_collator
        if data_args.pad_to_max_length
        else SimCseDataCollatorWithPadding(
            tokenizer=tokenizer, data_args=data_args, model_args=ModelArguments(do_mlm=False)
        )
    )

    # 평가 데이터셋 로드
    #eval_dataset = load_from_disk("data/datasets/dev")

    trainer = CLTrainer(
        model=model,
        args=training_args,
        train_dataset=combined_dataset,
        #eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    trainer.train()
    # 평가 수행 및 결과 출력
    #eval_results = trainer.evaluate(eval_dataset)
    #logger.info(f"Final Evaluation Results: {eval_results}")

    model.save_pretrained(f"{output_dir}/unsupervise_roberta-large")
    tokenizer.save_pretrained(f"{output_dir}/unsupervise_roberta-large")

if __name__ == "__main__":
    main()
