'use client';

import React from 'react';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from '@/components/ui/pagination';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface SamplesPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  maxVisiblePages?: number;
}

export function SamplesPagination({
  currentPage,
  totalPages,
  onPageChange,
  maxVisiblePages = 10
}: SamplesPaginationProps) {
  if (totalPages <= 1) return null;

  // Calculate which page numbers to show
  const getPageNumbers = (): (number | 'ellipsis')[] => {
    const pages: (number | 'ellipsis')[] = [];

    if (totalPages <= maxVisiblePages) {
      // Show all pages if total is less than max
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show first page
      pages.push(1);

      // Calculate start and end of visible range
      const rangeStart = Math.max(2, currentPage - 3);
      const rangeEnd = Math.min(totalPages - 1, currentPage + 3);

      // Add ellipsis if needed
      if (rangeStart > 2) {
        pages.push('ellipsis');
      }

      // Add middle pages
      for (let i = rangeStart; i <= rangeEnd; i++) {
        pages.push(i);
      }

      // Add ellipsis if needed
      if (rangeEnd < totalPages - 1) {
        pages.push('ellipsis');
      }

      // Show last page
      pages.push(totalPages);
    }

    return pages;
  };

  const pageNumbers = getPageNumbers();

  return (
    <Pagination className="py-8">
      <PaginationContent>
        {/* Previous Button */}
        <PaginationItem>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="h-10 w-10"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </PaginationItem>

        {/* Page Numbers */}
        {pageNumbers.map((page, index) => {
          if (page === 'ellipsis') {
            return (
              <PaginationItem key={`ellipsis-${index}`}>
                <PaginationEllipsis />
              </PaginationItem>
            );
          }

          return (
            <PaginationItem key={page}>
              <PaginationLink
                onClick={() => onPageChange(page)}
                isActive={currentPage === page}
                className="h-10 w-10 cursor-pointer"
              >
                {page}
              </PaginationLink>
            </PaginationItem>
          );
        })}

        {/* Next Button */}
        <PaginationItem>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="h-10 w-10"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
