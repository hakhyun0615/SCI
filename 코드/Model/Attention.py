import torch
import torch.nn as nn
import torch.nn.functional as F
    
class LSTMEncoder(nn.Module):
    def __init__(self, emb_dim, hid_dim, out_dim):
        super(LSTMEncoder, self).__init__()
        self.hid_dim = hid_dim
        self.lstm = nn.LSTM(input_size=emb_dim, hidden_size=hid_dim, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hid_dim, out_dim)

    # input : num * window_size * emb_dim
    def forward(self, input):
        # hidden, cell : 1 * num * hid_dim
        device = input.device
        hidden = torch.randn(1, input.shape[0], self.hid_dim).to(device)
        cell = torch.randn(1, input.shape[0], self.hid_dim).to(device)
        hiddens, (hidden, cell) = self.lstm(input, (hidden, cell))  # hiddens : num * window_size * emb_dim
        y_hat = self.fc(hidden[0])   # num * out_dim  
        return y_hat, hidden, cell    
    
class AttnLSTMDecoder(nn.Module):
    def __init__(self, emb_dim, hid_dim, out_dim, dropout):
        super(AttnLSTMDecoder, self).__init__()
        self.dropout = dropout

        self.lstm = nn.LSTM(input_size=emb_dim, hidden_size=hid_dim, dropout=dropout, batch_first=True)
        self.fc1 = nn.Linear(hid_dim + hid_dim, hid_dim)
        self.tanh = nn.Tanh()
        self.fc2 = nn.Linear(hid_dim, out_dim)

    # input : hid_dim
    # hidden : 1, num * hid_dim
    def forward(self, input, hidden):
        def dropout(inputs):
            if self.training:
                mask = (torch.rand(*inputs.shape)<self.dropout) / self.dropout
                inputs = inputs * mask
            return inputs

        query = input.unsqueeze(1)   # hid_dim, 1
        key = hidden[0]  # num * hid_dim
        value = hidden[0]  # num * hid_dim

        att_score = (key @ query)   # num, 1
        att_value = F.softmax(att_score, dim=0)  # num,1

        a = (att_value.permute(1,0) @ value).squeeze() # hid_dim
        s = torch.cat([query.squeeze(), a])  # 2hid_dim
        # s = dropout(s)
        s = self.fc1(s)  # hid_dim
        s = self.tanh(s)  # hid_dim

        y_hat = self.fc2(s) # oud_dim
        return y_hat
    
class LSTMSeq2Seq(nn.Module):
    def __init__(self, emb_dim, hid_dim, out_dim, dropout=0.):
        super(LSTMSeq2Seq, self).__init__()
        self.out_dim = out_dim
        self.emb_dim = emb_dim
        self.hid_dim = hid_dim
        self.dropout = nn.Dropout(dropout)

        self.encoder = LSTMEncoder(emb_dim, hid_dim, out_dim)
        self.decoder = AttnLSTMDecoder(emb_dim, hid_dim, out_dim, dropout)

    # src : num * emb_dim
    # index : trg 값이 있는 것
    def forward(self, src, index, mx_len):
        # Encoder 
        hiddens, hidden, cell = self.encoder(src)  # hidden : 1, num, hid_dim
        # Decoder
        y_hat = self.decoder(hidden[0][index], hidden[:,:mx_len,:])
        return y_hat