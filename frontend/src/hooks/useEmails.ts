import { useMutation, useQueryClient } from '@tanstack/react-query';
import { emailsApi } from '../api/client';

export function useProcessBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: emailsApi.processBatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}
