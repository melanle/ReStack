# import torch
# from transformers import BertTokenizer, BertForSequenceClassification, AdamW
# from torch.utils.data import DataLoader, Dataset

# # Mock dataset class
# class ResumeDataset(Dataset):
#     def __init__(self, resumes, job_descriptions, scores, tokenizer, max_length=512):
#         self.resumes = resumes
#         self.job_descriptions = job_descriptions
#         self.scores = scores
#         self.tokenizer = tokenizer
#         self.max_length = max_length
        
#     def __len__(self):
#         return len(self.resumes)
    
#     def __getitem__(self, idx):
#         text = self.job_descriptions[idx] + " [SEP] " + self.resumes[idx]
#         inputs = self.tokenizer(
#             text, 
#             truncation=True, 
#             padding='max_length', 
#             max_length=self.max_length,
#             return_tensors='pt'
#         )
#         return {
#             'input_ids': inputs['input_ids'].squeeze(0),
#             'attention_mask': inputs['attention_mask'].squeeze(0),
#             'labels': torch.tensor(self.scores[idx], dtype=torch.float)
#         }

# # Load tokenizer and model
# tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
# model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=1)  # Regression task

# # Define dataset and data loader (replace with your data)
# resumes = ["Sample resume text 1", "Sample resume text 2"]
# job_descriptions = ["Sample job description 1", "Sample job description 2"]
# scores = [85, 90]  # Replace with your actual scores

# dataset = ResumeDataset(resumes, job_descriptions, scores, tokenizer)
# loader = DataLoader(dataset, batch_size=2, shuffle=True)

# # Training loop (simplified example)
# optimizer = AdamW(model.parameters(), lr=5e-5)
# model.train()

# for epoch in range(3):  # Adjust epochs as needed
#     for batch in loader:
#         optimizer.zero_grad()
#         outputs = model(
#             input_ids=batch['input_ids'], 
#             attention_mask=batch['attention_mask'], 
#             labels=batch['labels'].unsqueeze(1)  # Adjust for single output regression
#         )
#         loss = outputs.loss
#         loss.backward()
#         optimizer.step()
#     print(f"Epoch {epoch+1} Loss: {loss.item()}")

# # Save the trained model
# torch.save(model.state_dict(), 'fine_tuned_bert_model.pth')
# print("Model saved successfully!")