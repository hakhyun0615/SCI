import pandas as pd
import torch
from torch.utils.data import Dataset

class NODE_Transformer_Dataset(Dataset):
    def __init__(self, transaction_data, economy_data, sequence_length=5):
        all_dong_max_apartment_complex = transaction_data.drop_duplicates(subset=['시군구','단지명']).groupby(['시군구'])['단지명'].count().max()

        date_range = pd.date_range('20060101', '20221201', freq='MS')
        economy_data.index = date_range
        transaction_data.drop_duplicates(subset=['시군구', '단지명', '계약년월'], keep='first', inplace=True) # 왜 rnn_transformer는 가능했지?
        dongs_x, dongs_y = [], []

        # 동별로 탐색
        for dong in transaction_data['시군구'].unique():
            filtered_data = transaction_data[transaction_data['시군구'] == dong]

            # 200601부터 sequence_length(window_size)만큼 탐색
            for idx in range(len(date_range)-sequence_length+1): # len(date_range)-sequence_length+1
                # x,y 포함된 기간 가져오기
                current_range = date_range[:idx+sequence_length+1]
                
                # x 기간에 sequence_length만큼 거래가 존재하는 단지만 가져오기(단, current_range_filtered_data에는 모든 기간 포함)
                current_range_apartment_complex = filtered_data[filtered_data['계약년월'].isin(current_range[:-1])].groupby('단지명').filter(lambda x: len(x) >= sequence_length)['단지명'].unique()
                current_range_filtered_data = filtered_data[filtered_data['단지명'].isin(current_range_apartment_complex)]

                # x 기간의 단지별 평단가, 시간, 경제(x 기간 중 마지막 window_size 만큼)
                current_range_filtered_x = current_range_filtered_data[current_range_filtered_data['계약년월'].isin(current_range[:-1])].groupby('단지명').apply(lambda x: x.tail(sequence_length)).reset_index(drop=True)
                grouped_current_range_filtered_x = current_range_filtered_x.groupby('단지명').agg({'평단가': list}).reset_index()['평단가'].to_list()
                grouped_current_range_filtered_time_x = current_range_filtered_x.groupby('단지명').agg({'계약년월': list}).reset_index()['계약년월'].to_list()
                grouped_current_range_filtered_time_x = [[float((ts.year-pd.Timestamp('2006-01').year)*12+(ts.month-pd.Timestamp('2006-01').month)) for ts in sublist] for sublist in grouped_current_range_filtered_time_x]
                grouped_current_range_filtered_economy_x = [[economy_data[ts]] for ts in current_range[-1-sequence_length:-1]]

                # y 기간의 단지별 평단가, 시간, 경제
                grouped_current_range_filtered_y = []
                grouped_current_range_filtered_time_y = []
                grouped_current_range_filtered_economy_y = []
                for apartment_complex in current_range_apartment_complex:
                    if current_range_filtered_data[current_range_filtered_data['단지명']==apartment_complex]['계약년월'].isin([current_range[-1]]).any():                
                        grouped_current_range_filtered_y.append(current_range_filtered_data[(current_range_filtered_data['단지명']==apartment_complex) & (current_range_filtered_data['계약년월']==current_range[-1])]['평단가'].to_list())
                    else:
                        grouped_current_range_filtered_y.append([0.0])
                    grouped_current_range_filtered_time_y.append([current_range[-1]])
                grouped_current_range_filtered_time_y = [[float((ts.year-pd.Timestamp('2006-01').year)*12+(ts.month-pd.Timestamp('2006-01').month)) for ts in sublist] for sublist in grouped_current_range_filtered_time_y]
                grouped_current_range_filtered_economy_y.append([economy_data[current_range[-1]]])
                
                # 최대 단지 수만큼 단지별 평단가 채우기
                if len(grouped_current_range_filtered_x) < all_dong_max_apartment_complex:
                    for _ in range(all_dong_max_apartment_complex-len(grouped_current_range_filtered_x)):
                        grouped_current_range_filtered_x.append([0.0]*sequence_length)
                        grouped_current_range_filtered_time_x.append([0.0]*sequence_length)
                        grouped_current_range_filtered_y.append([0.0])
                        grouped_current_range_filtered_time_y.append([0.0])

                # x,y 단지별 평단가, 시간, 경제 모두 묶고 dongs에 하나씩 붙이기
                grouped_current_range_filtered_and_time_and_economy_x = []
                grouped_current_range_filtered_and_time_and_economy_x.extend([grouped_current_range_filtered_x, grouped_current_range_filtered_time_x, grouped_current_range_filtered_economy_x])
                grouped_current_range_filtered_and_time_and_economy_y = []
                grouped_current_range_filtered_and_time_and_economy_y.extend([grouped_current_range_filtered_y, grouped_current_range_filtered_time_y, grouped_current_range_filtered_economy_y])
                dongs_x.append(grouped_current_range_filtered_and_time_and_economy_x)
                dongs_y.append(grouped_current_range_filtered_and_time_and_economy_y)

        self.dongs_x = dongs_x
        self.dongs_y = dongs_y
        self.len = len(dongs_x)

    # 부동산_x, 시간_x, 경제_x, 부동산_y, 시간_y, 경제_y 
    def __getitem__(self, i):
        return torch.FloatTensor(self.dongs_x[i][0]), torch.FloatTensor(self.dongs_x[i][1]), torch.FloatTensor(self.dongs_x[i][2]), torch.FloatTensor(self.dongs_y[i][0]), torch.FloatTensor(self.dongs_y[i][1]), torch.FloatTensor(self.dongs_y [i][2])
 
    def __len__(self):
        return self.len
