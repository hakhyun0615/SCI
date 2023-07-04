import torch.nn as nn

class Auto(nn.Module):
      def __init__(self, input_size=7):
            super(Auto, self).__init__()

            # 인코더(encoder) 정의
            self.encoder = nn.Sequential(
                  nn.Linear(input_size, 4),
                  nn.ReLU(),
                  nn.Linear(4, 2),
                  nn.ReLU()
            )

            # 디코더(decoder) 정의
            self.decoder = nn.Sequential(
                  nn.Linear(2, 4),
                  nn.ReLU(),
                  nn.Linear(4, input_size),
                  nn.Sigmoid()
            )

      def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded