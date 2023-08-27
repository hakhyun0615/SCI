import pandas as pd
import torch
from torch.utils.data import Dataset
from utils import price_per_pyeong_fill_0

class RNN_Transformer_Dataset(Dataset):
    def __init__(self, data, sequence_length=5):
        all_dong_max_apartment_complex = data.drop_duplicates(subset=['시군구','단지명']).groupby(['시군구'])['단지명'].count().max()

        filled_data = price_per_pyeong_fill_0(data)
        filled_data = filled_data[['시군구', '단지명', '계약년월', '평단가']]        
        
        dongs_x, dongs_y = [], []
        for dong in filled_data['시군구'].unique():
            dong_x, dong_y = [], []
            filtered_filled_data = filled_data[filled_data['시군구'] == dong]
            date_range = pd.date_range('20060101', '20221201', freq='MS')
            for idx in range(len(date_range)-sequence_length):
                current_range_x = date_range[idx:idx+sequence_length]
                current_range_y = date_range[idx+sequence_length:idx+sequence_length+1]
                current_range_filled_x = filtered_filled_data[filtered_filled_data['계약년월'].isin(current_range_x)]
                current_range_filled_y = filtered_filled_data[filtered_filled_data['계약년월'].isin(current_range_y)]
                grouped_current_range_filled_x = current_range_filled_x.groupby('단지명').agg({'평단가': list}).reset_index()['평단가'].to_list()
                grouped_current_range_filled_y = current_range_filled_y.groupby('단지명').agg({'평단가': list}).reset_index()['평단가'].to_list()
                if len(grouped_current_range_filled_x) < all_dong_max_apartment_complex:
                    for _ in range(all_dong_max_apartment_complex-len(grouped_current_range_filled_x)):
                        grouped_current_range_filled_x.append([0.0]*sequence_length)
                        grouped_current_range_filled_y.append([0.0])
                dong_x.append(grouped_current_range_filled_x)
                dong_y.append(grouped_current_range_filled_y)
            dongs_x.append(dong_x)
            dongs_y.append(dong_y)

        self.dongs_x = dongs_x
        self.dongs_y = dongs_y
        self.len = len(dongs_x)

    def __getitem__(self, i):
        return torch.FloatTensor(self.dongs_x[i]), torch.FloatTensor(self.dongs_y[i])

    def __len__(self):
        return self.len